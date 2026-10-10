"""ADAPTATION: export only P1 provenance and lossless sanitized evidence.

Wheels/source trees/private command/native logs never enter the public checkout.
No historical result or scientific gate is rewritten.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.m5_p1_diagnostic import canonical,sha,save
from scripts.m5_p1_compare import difference,compact_decision,numeric_digest


def load(p):return json.loads(p.read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--supplement',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/m5/patch-p1')
    args=parser.parse_args()
    args.execution=args.execution.resolve();args.build=args.build.resolve()
    args.comparison=args.comparison.resolve();args.supplement=args.supplement.resolve()
    dest=args.output.resolve();dest.mkdir(parents=True,exist_ok=True)
    data=dest/'data';data.mkdir(exist_ok=False)
    private_root=str(ROOT.parents[1])
    def sanitize(v):
        if isinstance(v,str):return v.replace(private_root,'<project>')
        if isinstance(v,list):return [sanitize(x) for x in v]
        if isinstance(v,dict):return {k:sanitize(x) for k,x in v.items()}
        return v
    execution=load(args.execution/'execution-private.json')
    manifest=load(args.build/'build-manifest.json');supplement=load(args.supplement)
    manifest['toolchain_supplement']=supplement
    resource=args.supplement.parent/'resource-snapshot-public.json'
    if resource.exists():
        manifest['execution_resource_observation']=load(resource)
        save(data/'resource-observation.json',load(resource))
    save(dest/'build-manifest.json',sanitize(manifest))
    before=load(args.execution/'preservation-before-private.json');after=load(args.execution/'preservation-after-private.json')
    preservation=dict(equal=before==after,formal_file_count=len(before['formal_environment']),
        baseline_file_count=len(before['baseline_source']),
        before_sha256=sha(canonical(before)),after_sha256=sha(canonical(after)),
        formal_environment_before_sha256=sha(canonical(before['formal_environment'])),
        formal_environment_after_sha256=sha(canonical(after['formal_environment'])),
        baseline_source_before_sha256=sha(canonical(before['baseline_source'])),
        baseline_source_after_sha256=sha(canonical(after['baseline_source'])),
        excluded='interpreter-created .pyc/__pycache__ only; no binaries/package sources excluded')
    save(dest/'preservation.json',preservation)
    save(data/'preservation-files.json',sanitize(dict(before=before,after=after)))
    rng_data={label:load(args.execution/label/'rng.json') for label in ('A','B','C')}
    control_streams={label:{name:[r['cycles'][0] for r in rng_data[label]['experiments'] if r['function']==name][0]
        for name in ('gen_pcg_set_seed','avx_pcg_set_seed')} for label in ('A','B','C')}
    unchanged_control_equal=control_streams['A']==control_streams['B']==control_streams['C']
    save(dest/'rng-data.json',dict(controls=rng_data,unchanged_integer_controls_equal=unchanged_control_equal))
    strict={}
    for label in ('A','B','C'):
        directory=args.execution/label
        api=load(directory/'api/raw-before-assertions.json')
        prefix=load(directory/'prefix-capture.json')
        api_diff=difference(api[0],api[1]);prefix_diff=difference(prefix['full'][:24],prefix['short'])
        strict[label]=dict(api_exit=execution['controls'][label]['api_receipt']['exit_code'],
            generation_exit=execution['controls'][label]['replay_receipt']['exit_code'],
            prefix_exit=execution['controls'][label]['prefix_receipt']['exit_code'],
            api_first_difference=api_diff,prefix_first_difference=prefix_diff)
        save(data/f'{label}-strict-api-raw.json',api)
        save(data/f'{label}-strict-prefix-raw.json',sanitize(prefix))
        save(data/f'{label}-auto-path-fit.json',load(directory/'auto-path-fit.json'))
    save(dest/'strict-data.json',strict)
    inspection={}
    for label in ('B','C'):
        seeder=(args.build/f'{label}-seeder.stdout').read_text()
        core=(args.build/f'{label}-serial-core.stdout').read_text()
        lines=core.splitlines();indices=[i for i,line in enumerate(lines) if 'local_pcg_set_seed' in line]
        excerpt='\n'.join('\n'.join(lines[max(0,i-5):i+13]) for i in indices)
        prior_read=bool(re.search(r'\b(?:mov|add|imul)\s+0x20\(%rdi\),',seeder))
        inspection[label]=dict(prior_byte32_read=prior_read,
            serial_callback_reference=bool(indices),serial_indirect_call='call' in excerpt and '*(%rax)' in excerpt)
        (data/f'{label}-seeder-disassembly.txt').write_text('\n'.join(line.rstrip() for line in sanitize(seeder).splitlines())+'\n')
        (data/f'{label}-serial-core-excerpt.txt').write_text('\n'.join(line.rstrip() for line in sanitize(excerpt).splitlines())+'\n')
        for name in ('ldd','elf'):
            content=sanitize((args.build/f'{label}-{name}.stdout').read_text())
            (data/f'{label}-{name}.txt').write_text('\n'.join(line.rstrip() for line in content.splitlines())+'\n')
    save(dest/'binary-inspection.json',inspection)
    matrix=load(args.comparison/'comparison.json')
    save(dest/'matrix-data.json',sanitize(matrix))
    for p in args.comparison.iterdir():
        if p.is_dir():
            target=data/p.name;target.mkdir()
            for f in p.glob('*.json'):save(target/f.name,sanitize(load(f)))
    for entry in execution['batches']:
        run=args.execution/entry['run_id'];target=data/entry['run_id']
        if not target.exists():target.mkdir()
        for name in ('manifest.json','expected-run-ledger.json','artifact-ledger-private.json','worker-receipts-private.json'):
            if (run/name).exists():save(target/name.replace('-private',''),sanitize(load(run/name)))
        worker_receipts=load(run/'worker-receipts-private.json')
        receipt_index={r['path']:i for i,r in enumerate(worker_receipts)}
        fit_provenance=[]
        for directory in ('reference','decisions'):
            for path in sorted((run/directory).rglob('fit-*.json')):
                if '.command.' in path.name:continue
                fit=load(path);parent=str(path.parent.relative_to(run))
                fit_provenance.append(dict(path=str(path.relative_to(run)),
                    artifact_sha256=sha(path.read_bytes()),
                    code_identity_ref='build-manifest.json/toolchain_supplement/sampling_code_hashes',
                    frozen_model_identity_ref='protocol.json/immutable_hashes',
                    interpreter_sha256=fit['interpreter_sha256'],native_binary_sha256=fit['native_binary_sha256'],
                    input_sha256=fit['input_sha256'],worker_receipt_index=receipt_index[parent],
                    native_receipt=str(path.with_suffix('.command.json').relative_to(run)) if directory=='decisions' else None,
                    receipt_kind='native-child' if directory=='decisions' else 'shared-reference-worker',
                    candidate_validation=fit['candidate_validation']))
        save(target/'fit-provenance.json',dict(fits=fit_provenance,
            note='Same-process reference calls share one bounded worker receipt; no per-call wall-time is inferred.'))
    receipts=[]
    for p in sorted(args.build.glob('*.command.json')):
        receipts.append(dict(category='build',private_log=str(p.relative_to(ROOT)),**load(p)))
    for label,control in execution['controls'].items():
        for name in ('rng_receipt','api_receipt','replay_receipt','prefix_receipt'):
            receipts.append(dict(category=label+'/'+name,**control[name]))
    receipts.extend(dict(category='matrix/'+b['run_id'],**b['receipt']) for b in execution['batches'])
    receipts.extend(dict(category='regression/'+name,**r) for name,r in execution['regressions'].items())
    source_diff=[k for k in manifest['builds']['B']['source_files'] if manifest['builds']['B']['source_files'][k]!=manifest['builds']['C']['source_files'][k]]
    source_pass=(source_diff==['ext_src/abc_rand_pcg_local_avx512.c'] and manifest['builds']['B']['abi']==manifest['builds']['C']['abi']
        and all(r['exit_code']==0 for r in receipts if r['category']=='build'))
    c=rng_data['C']
    rng_pass=(c['corrected_reference_matches'] and c['prior_content_independent'] and c['reused_buffer_repeats']
        and unchanged_control_equal and all(c['unmodified_control_independence'].values())
        and inspection['B']['prior_byte32_read'] and not inspection['C']['prior_byte32_read']
        and inspection['C']['serial_callback_reference'] and inspection['C']['serial_indirect_call']
        and c['normal_auto_dispatch']==dict(cpu_current=3,seed_function='avx512_pcg_set_seed'))
    strict_pass=all(strict['C'][k]==0 for k in ('api_exit','generation_exit','prefix_exit'))
    regression_pass=all(r['exit_code']==0 for r in execution['regressions'].values())
    gates=dict(source_build_ABI='PASS' if source_pass else 'FAIL',
        RNG_prior_memory_repair='PASS' if rng_pass else 'FAIL',
        original_strict_assertions='PASS' if strict_pass else 'FAIL',
        full_posterior_repeatability=matrix['C_numerical'],
        native_validity_candidate_iteration_stability=matrix['C_decisions'] if matrix['C_integrity']=='PASS' else matrix['C_integrity'],
        reporter_detection_privacy_data_integrity='PENDING_PUBLIC_PRIVACY' if regression_pass and before==after and matrix['C_integrity']=='PASS' else 'FAIL',
        scientific_validity_runtime_adoption_M6='NOT_APPROVED/OPEN')
    validation=dict(task='M5-P1',machine='node-0',gpu_experiment=False,final_alert=False,gates=gates,
        engineering_overall='PENDING_PUBLIC_PRIVACY' if all(x in ('PASS','PENDING_PUBLIC_PRIVACY') for k,x in gates.items() if k!='scientific_validity_runtime_adoption_M6') else 'FAIL',
        controls=strict,matrix_integrity=matrix['C_integrity'],preservation=preservation,
        private_execution='runs/m5-p1-execution-01',private_build='runs/m5-p1-build-01',
        receipts=sanitize(receipts),code_identity=supplement['code_hashes'],
        orchestration_exit_is_not_acceptance=True,public_wheel_distribution='BLOCKED_LICENSE_REVIEW')
    save(dest/'validation.json',validation)
    table='| Build | API exit | Prefix exit | RNG prior independence | Reuse | Correct integer reference |\n|---|---:|---:|---|---|---|\n'
    for label in ('A','B','C'):
        r=rng_data[label];s=strict[label]
        table+=f"| {label} | {s['api_exit']} | {s['prefix_exit']} | {r['prior_content_independent']} | {r['reused_buffer_repeats']} | {r['corrected_reference_matches']} |\n"
    (dest/'STRICT_RESULTS.md').write_text('# Original unchanged strict assertions\n\n'+table+
        '\nC independently generates complete sustained replay, then independently computes\n'
        'the short prefix using original tests/m5_replay.py bytes. P1 capture wrapper\n'
        'uses finally to retain globals; original assertions/exceptions propagate.\n'
        'Source hashes match protocol.json. No slicing to fabricate short execution,\n'
        'no version monkeypatch, tolerance, skip, xfail or exception-to-exit0.\n'
        'All first differences and full raw trees are in strict-data.json and data/.\n'
        'A/B failures remain control results, including B API occasional success.\n'
        'Native stdout/stderr and actual commands/exits stay in the private run;\n'
        'validation.json lists sanitized receipts with private evidence references.\n')
    (dest/'RNG_VALIDATION.md').write_text('# RNG causal validation\n\n'+table+
        '\nThe independent scalar uint64 reference implements source seed preprocessing,\n'
        'modulo arithmetic, state lane order0,4,1,5,2,6,3,7, PCG XSH-RR output and\n'
        'eight scalar steps per lane; it does not read old_word. Full64-output reference\n'
        'and all prior-word0/1/0x123456789abcdef0, fill0/0xa5, repeats and reused-buffer\n'
        'cycles are in rng-data.json. Initializing diagnostic buffers never modifies\n'
        'production objects/globals. Layout is measured from release headers.\n\n'
        f'Unmodified generic/AVX2 integer control streams equal across A/B/C: {unchanged_control_equal}.\n'
        'C seeder no longer reads prior byte32; it uses computed registers, so a\n'
        'literal byte64 load is not required. B still reads byte32. Binary excerpts\n'
        'show serial core loads selected local_pcg_set_seed and calls indirectly;\n'
        'actual normal auto fit selects avx512_pcg_set_seed, CPU_CURRENT3.\n\n'
        'This is a bounded one-series defect intervention, not multi-pixel/reentrant\n'
        'thread safety or BEAST posterior equality across ISAs. No scientific adoption.\n')
    rows='| Build/batch | Reference fits | Native decision fits | Prefixes | Integrity issues | Native validation errors |\n|---|---:|---:|---:|---:|---:|\n'
    for m in matrix['matrices']:
        count=m.get('counts',{})
        rows+=f"| {m['build']}/{m['batch']} | {count.get('reference_fits','MISSING')} | {count.get('native_decision_fits','MISSING')} | {count.get('prefixes','MISSING')} | {len(m['integrity_errors'])} | {m.get('native_errors','UNKNOWN')} |\n"
    (dest/'MATRIX_RESULTS.md').write_text('# Full exact numerical matrices\n\n'+rows+
        f"\nCandidate C full-posterior gate: **{matrix['C_numerical']}**; integrity: **{matrix['C_integrity']}**.\n"
        'matrix-data.json gives every cell and combined same-model/actual-ISA group,\n'
        'including inherited versus fixed affinity/thread environment, same/fresh\n'
        'process and both batches. Requested AVX512 spelling is not treated as\n'
        'proof of dispatch. Cross-ISA posterior equality is not required.\n\n'
        'All logical trees and24 arrays/fit are exported losslessly with dtype,shape,\n'
        'base64 bytes and SHA256. Comparison preserves NaN payload/signed zero and\n'
        'does not mix PID/path/time metadata into numeric digests. First differences\n'
        'are retained; no failures/samples are discarded. Complete expected/actual\n'
        'ledgers and independently checked inputs/model/fixture/byte counts accompany\n'
        'each batch. Measurement completion is not acceptance.\n')
    with (dest/'MATRIX_RESULTS.md').open('a') as f:
        f.write('\nInputs are iteration times in ms: the reference is30 float64 samples/240\n'
          'bytes; mcmc_samples8000 is a different sample count. Receipt elapsed_s is\n'
          'seconds and is not CUDA Event/collective timing. Inherited reference\n'
          'worker affinity/thread counts and pinned observations are exported.\n'
          'An owned-process point inspection confirms decision/native workers on\n'
          'CPU0 with all four thread variables1. Full batches effectively run at\n'
          'nice19 because nested nice10 saturates, versus protocol nominal10; this\n'
          'lower priority is identical for B/C and never used for a performance\n'
          'claim. Sampling code, seed, model, thread settings and order are unchanged.\n')
    (dest/'DECISION_RESULTS.md').write_text('# Candidate and first-observation stability\n\n'+rows+
        f"\nCandidate C decision/native-validity gate: **{gates['native_validity_candidate_iteration_stability']}**.\n"
        'All seven fixtures have20 complete45-prefix replays per build/batch. Each\n'
        'real fit uses a new interpreter, original30s timeout and original filtering.\n'
        'Ten no-fit prefixes/replay use original retained-sample guards, never zeros\n'
        'or fake fits. Both20% denominators, probability-qualified/filtered cp sets,\n'
        'candidate presence, first observing iteration and every filter stage remain.\n'
        'Per-prefix posterior-byte equality is checked across all40 repetitions,\n'
        'independently of candidate stability. Errors remain distinct from no candidate.\n\n'
        'Strong fixture stability does not establish behavior near cpPr0.8, production\n'
        'false-positive rate, GPU fault precision/recall or paper1–2 iteration latency.\n'
        'G01/G02/G04/G09/G13/G20 stay OPEN; final_alert=false.\n')
    index=[dict(path=str(p.relative_to(dest)),size=p.stat().st_size,sha256=sha(p.read_bytes()))
           for p in sorted(data.rglob('*')) if p.is_file()]
    save(dest/'data-index.json',dict(files=index))
    print(json.dumps(dict(gates=gates,public_data_files=len(index),public_data_bytes=sum(x['size'] for x in index))))


if __name__=='__main__':main()
