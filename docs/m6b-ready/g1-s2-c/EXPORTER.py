"""ADAPTATION: copy complete numerical evidence, redact identities in receipts.

No fit/comparison/threshold is recalculated here. Standard-library independent
array-byte verification checks transport; unchanged P1 comparator is authoritative.
"""
from pathlib import Path
import argparse,base64,hashlib,json,re,shutil,struct
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--repo',type=Path,required=True);a=p.parse_args()
    raw=a.raw;repo=a.repo;run=raw/'execution01';dest=repo/'docs/m6b-ready/g1-s2-c'
    result=json.loads((run/'execution-private.json').read_text())
    first=json.loads((raw/'driver.receipt.json').read_text())
    finish=raw/'finish02';acceptance=json.loads((finish/'acceptance.json').read_text())
    final=json.loads((raw/'finisher.receipt.json').read_text())
    assert first['exit_code']==1 and not first['timeout']
    assert result['error']=='AssertionError: m6b_ready_cursor_contract failed; evidence retained'
    assert acceptance['original_data_immutable'] and acceptance['formal_preserved'] and acceptance['source_preserved']
    assert final['exit_code']==0 and not final['timeout'] and final['child_finished']
    assert acceptance['status']=='PASS_ISOLATED_C_CPU_GATES_ONLY'
    full_audit=json.loads((raw/'formal-full-audit.json').read_text());assert len(full_audit['additional_files'])==915
    assert result['formal_preserved'] and result['source_preserved']
    before=json.loads((run/'formal-before.json').read_text());after=json.loads((run/'formal-after.json').read_text());assert before==after
    assert (raw/'historical-protection-before.json').read_bytes()==(raw/'historical-protection-after.json').read_bytes()
    candidate=result['identity']['native_file'];environment=result['identity']['sys_prefix']
    project=str(Path(environment).parents[3]);server_run=str(Path(environment).parent.parent)
    aliases={};mapping=[]
    def redact(v,key=''):
        if key=='metadata' and isinstance(v,dict):
            # Third-party long descriptions remain private; exact raw metadata
            # fingerprints and installation-relevant header fields are public.
            return {name:dict(raw_sha256=sha(body.encode()),headers=[line for line in body.split('\n\n',1)[0].splitlines()
                if line.startswith(('Name:','Version:','Requires-Python:','Requires-Dist:','License:','Wheel-Version:','Generator:','Root-Is-Purelib:','Build:','Tag:'))])
                for name,body in v.items()}
        if key in ('pid','pgid','ppid') and isinstance(v,int):
            if v not in aliases:aliases[v]='owned-process-'+str(len(aliases)+1)
            return aliases[v]
        if isinstance(v,dict):return {k:redact(x,k) for k,x in v.items()}
        if isinstance(v,list):return [redact(x,key) for x in v]
        if isinstance(v,str):
            v=v.replace(environment,'<isolated-c>').replace(server_run,'<s2-private-run>').replace(project,'<project>')
            v=re.sub(r'/(?:home|Users)/[A-Za-z0-9_.-]+(?:/[^\s\"\']*)?', '<private-path>',v)
            v=re.sub(r'\bgpu-0[12]\b','node-0',v)
            if key=='mapped_library_lines':v='<candidate C native mapping observed; raw range/inode private>'
            if key=='':v=re.sub(r'0x[0-9a-fA-F]{12,}', '<runtime-address>',v)
            return v
        return v
    def emit(source,target,structured=False):
        data=source.read_bytes()
        if structured:
            public=(json.dumps(redact(json.loads(data)),sort_keys=True,separators=(',',':'))+'\n').encode()
        else:public=redact(data.decode()).encode()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(public)
        mapping.append(dict(private_file=str(source.relative_to(raw)),raw_sha256=sha(data),public_file=str(target.relative_to(repo)),public_sha256=sha(public)))
    def save(name,value):(dest/name).write_text(json.dumps(redact(value),sort_keys=True,indent=2)+'\n')
    assert json.loads((run/'auto-path-fit.json').read_text())['candidate_validation']=='PASS'
    assert json.loads((run/'auto-path-fit.json').read_text())['candidate_validation_error'] is None
    for file in ['preflight.json','identity.json','rng.json','auto-path-fit.json','runtime.lock','prefix-capture.json','api/raw-before-assertions.json','api/contract.json','replay/sustained.json','arithmetic-evidence.json','field-contract/raw.json','field-contract/contract.json']:
        emit(run/file,dest/'runtime'/file,structured=file.endswith('.json'))
    comparison=json.loads((finish/'comparison/comparison.json').read_text())
    for key in ('C_integrity','C_numerical','C_native_validity','C_decisions'):assert comparison[key]=='PASS'
    # Copy original comparator outputs with every array byte. No redaction of
    # scientific values; identity-free comparator data must be byte-preserved.
    arrays=0;array_bytes=0
    for source in sorted((finish/'comparison').rglob('*.json')):
        data=source.read_bytes();value=json.loads(data)
        def walk(v):
            nonlocal arrays,array_bytes
            if isinstance(v,dict):
                if set(('dtype','shape','bytes_base64','sha256')).issubset(v):
                    b=base64.b64decode(v['bytes_base64'],validate=True);assert sha(b)==v['sha256']
                    size=int(re.search(r'(\d+)$',v['dtype']).group(1));count=1
                    for n in v['shape']:count*=n
                    assert len(b)==size*count;arrays+=1;array_bytes+=len(b)
                else:
                    for item in v.values():walk(item)
            elif isinstance(v,list):
                for item in v:walk(item)
        walk(value)
        assert b'/home/' not in data and b'/Users/' not in data
        target=dest/'data'/source.relative_to(finish/'comparison');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        mapping.append(dict(private_file=str(source.relative_to(raw)),raw_sha256=sha(data),public_file=str(target.relative_to(repo)),public_sha256=sha(data),byte_preserved=True))
    assert arrays==265920,(arrays,'missing full arrays')
    for source in sorted([*run.glob('*.command.json'),*finish.glob('*.command.json'),*raw.glob('*.command.json')]):
        emit(source,dest/'commands'/source.name,True)
        for suffix in ('.stdout','.stderr'):
            log=source.with_suffix('').with_suffix(suffix)
            emit(log,dest/'logs'/(log.name+'.txt'))
    for source in [raw/'driver.receipt.json',raw/'driver-start.json',raw/'finisher.receipt.json',raw/'finisher-start.json',raw/'pip-check.receipt.json',raw/'native-gate-audit.receipt.json']:
        emit(source,dest/'commands'/source.name,True)
    for source in [raw/'driver.stdout',raw/'driver.stderr',raw/'finisher.stdout',raw/'finisher.stderr',raw/'pip-check.stdout',raw/'pip-check.stderr',raw/'native-gate-audit.stdout',raw/'native-gate-audit.stderr']:
        emit(source,dest/'logs'/(source.name+'.txt'))
    # Full worker and native child command receipts are indexed and published;
    # native raw stdout/stderr SHA stay bound to private files, with all raw data
    # above losslessly available for independent numerical inspection.
    raw_index=[]
    for batch in ('s2-c-batch01','s2-c-batch02'):
        for file in ('manifest.json','expected-run-ledger.json','worker-receipts-private.json','artifact-ledger-private.json'):
            emit(run/batch/file,dest/'batches'/batch/file,True)
        native_receipts=[]
        for source in sorted((run/batch/'decisions').rglob('fit-*.command.json')):
            r=json.loads(source.read_text());assert r['exit_code']==0 and not r['timeout'] and r['raw_capture']=='PRESENT'
            native_receipts.append(dict(file=str(source.relative_to(raw)),raw_sha256=sha(source.read_bytes()),receipt=r,
               stdout_sha256=sha(source.with_suffix('').with_suffix('.stdout').read_bytes()),stderr_sha256=sha(source.with_suffix('').with_suffix('.stderr').read_bytes())))
        save('batches/'+batch+'/native-command-index.json',native_receipts)
    for source in sorted(raw.rglob('*')):
        if not source.is_file() or '.venv-m5-s2-c' in source.parts or 'wheels' in source.parts or 'checkout' in source.parts or source.name.endswith('.bundle'):continue
        raw_index.append(dict(file=str(source.relative_to(raw)),size=source.stat().st_size,sha256=sha(source.read_bytes())))
    # Preserve formal/source manifests without distributing third-party content.
    emit(run/'formal-before.json',dest/'formal-files.json',True)
    emit(run/'source-before.json',dest/'source-files.json',True)
    save('preservation.json',dict(formal_file_count=len(before),formal_before_after_equal=before==after,
        original_native_sha256=next(v for k,v in after.items() if 'Rbeast/' in k and k.endswith('.so')),
        source_file_count=len(json.loads((run/'source-before.json').read_text())),source_before_after_equal=result['source_preserved'],
        historical_raw_files=sum(len(v) for v in json.loads((raw/'historical-protection-before.json').read_text()).values()),
        historical_raw_equal=True,historical_before_sha256=sha((raw/'historical-protection-before.json').read_bytes()),
        historical_after_sha256=sha((raw/'historical-protection-after.json').read_bytes()),
        historical_snapshot_timing='taken during first C matrix, after isolated install; verified after full run, alongside byte-preserved historical source and fixed preflight formal snapshot'))
    save('postflight.json',dict(driver_actual_exit=final['exit_code'],driver_timeout=final['timeout'],first_driver_actual_exit=first['exit_code'],finisher_actual_exit=final['exit_code'],all_driver_children_waited=True,
        direct_active_child=result['own_current_child'],observed_owned_remaining=final['observed_owned_remaining'],
        formal_adoption='NOT_APPROVED',environment_kept_private=True,new_redis_gpu_resources=0,rollback='Do not enable new environment; original interpreter remains unchanged'))
    save('transport-array-audit.json',dict(machine='local-macOS',standard_library_only=True,arrays=arrays,array_bytes=array_bytes,
        dtype_shape_size_and_base64_sha_verified=True,scientific_data_redaction=False,comparison_files_byte_preserved=True))
    save('validation.json',dict(task=result['task'],status=acceptance['overall_acceptance'],cpu_gate_status=acceptance['status'],machine='node-0',execution_head=result['execution_head'],
        execution_tree=result['execution_tree'],execution_source_sha=result['execution_source_sha'],
        baseline_head='3ba7dad2070ad13466b4f14562ee54fa4a3e818b',first_driver=first,finisher=final,source_repair=acceptance,
        required_gates={k:comparison[k] for k in ('C_integrity','C_numerical','C_native_validity','C_decisions')},
        batches=[dict(name=m['run_id'],counts=m['counts'],integrity_errors=m['integrity_errors'],native_errors=m['native_errors'],fit_errors=m['fit_errors']) for m in comparison['matrices']],
        direct_receipts=result['receipts']+acceptance['receipts'],strict_original_assertions='PASS; original bytes unchanged',
        final_alert=False,scientific_validity='NOT_APPROVED/OPEN',formal_adoption='NOT_APPROVED',gpu='NOT_RUN',M6B='NOT_RUN',
        old_failures='M5-R/A/B FAIL and three NOT_CAPTURED preserved; not rerun under formal environment',
        source_and_approval='APPROVAL.md plus tasks/06b_ready_g1_s2_c.md',license_privacy_history='DEFERRED/OPEN; wheels/third-party source not published'))
    for name in ('postflight-private.json','native-gate-audit.json','formal-full-audit.json'):
        emit(raw/name,dest/name,True)
    for name in ('acceptance.json','original-data-before.json','cursor-contract/observations.json'):
        source=finish/name
        if source.exists():emit(source,dest/'continuation'/name,True)
    save('full-manifest-gap.json',dict(status='BLOCKED',preinstall_complete_manifest='NOT_CAPTURED',preinstall_noncache_files=1424,actual_all_files=2339,uncovered_cache_files=915,postinstall_full_manifest_preserved=True,no_automatic_adoption=True))
    save('raw-index.json',raw_index);save('raw-public-correspondence.json',mapping)
    shutil.copyfile(Path(__file__),dest/'EXPORTER.py')
    print(json.dumps(dict(export='PASS',arrays=arrays,byte_preserved_comparison=True,public_files=len(list(dest.rglob('*'))))))

if __name__=='__main__':main()
