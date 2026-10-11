"""ADAPTATION: finish only tests not executed after a new-runner CLI defect.

Never reruns fits or modifies original execution/batch files, fixtures or tests.
The first failed parent and argparse exit2 are required retained evidence.
"""
import argparse,hashlib,json,signal,sys
from pathlib import Path
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    run=a.run.resolve();project=a.project.resolve();assert run.is_relative_to(project/'runs')
    repo=run/'checkout';sys.path.insert(0,str(repo))
    from scripts import m6b_ready_s2_execute as driver
    signal.signal(signal.SIGTERM,driver.interrupted)
    original=run/'execution01';dest=run/'finish02';dest.mkdir(exist_ok=False)
    first=json.loads((run/'driver.receipt.json').read_text());execution=json.loads((original/'execution-private.json').read_text())
    assert first['exit_code']==1 and not first['timeout']
    assert execution['error']=='AssertionError: m6b_ready_cursor_contract failed; evidence retained'
    assert execution['receipts'][-1]['label']=='m6b_ready_cursor_contract' and execution['receipts'][-1]['exit_code']==2
    assert all(r['exit_code']==0 and not r['timeout'] for r in execution['receipts'][:-1])
    assert len(execution['batches'])==2 and all(b['receipt']['exit_code']==0 for b in execution['batches'])
    raw_before={str(f.relative_to(original)):digest(f) for f in sorted(original.rglob('*')) if f.is_file() and '.venv-m5-s2-c' not in f.parts and 'wheels' not in f.parts}
    driver.save(dest/'original-data-before.json',raw_before)
    result=dict(status='IN_PROGRESS',first_driver_retained_exit=first['exit_code'],first_cursor_argparse_retained_exit=2,
                source_head=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
                runner_source_sha256=digest(repo/'scripts/m6b_ready_s2_execute.py'),finisher_sha256=digest(Path(__file__)),
                receipts=[],native_fit_retries=0,models_fixtures_assertions_comparator_changed=False)
    py=str(original/'.venv-m5-s2-c/bin/python')
    def call(label,argv,deadline=120):
        r=driver.execute(argv,dest/(label+'.run'),deadline,driver.clean_env(True))
        result['receipts'].append(dict(label=label,**r));driver.save(dest/'progress.json',result)
        print(label,r['exit_code'],flush=True);assert r['exit_code']==0 and not r['timeout'],label
    try:
        call('cursor-contract-correct-argv',[py,'tests/m6b_ready_cursor_contract.py','--output',str(dest/'cursor-contract')])
        call('cursor-extra',[py,'tests/m6b_ready_cursor_extra.py'])
        call('privacy-unit',[py,'tests/privacy_check_test.py'])
        call('complete-comparison',[py,'scripts/m5_p1_compare.py','--execution',str(original),'--build',str(project/'runs/m5-p1-work/runs/m5-p1-build-01'),'--output',str(dest/'comparison')],900)
        comparison=json.loads((dest/'comparison/comparison.json').read_text())
        assert all(comparison[k]=='PASS' for k in ('C_integrity','C_numerical','C_native_validity','C_decisions'))
        result['required_matrix_gates']={k:comparison[k] for k in ('C_integrity','C_numerical','C_native_validity','C_decisions')}
        result['status']='PASS_ISOLATED_C_CPU_GATES_ONLY'
        result['overall_acceptance']='BLOCKED_FULL_FORMAL_MANIFEST_PREINSTALL_NOT_CAPTURED'
    except BaseException as error:
        result['status']='FAIL_OR_BLOCKED';result['error']=type(error).__name__+': '+str(error);raise
    finally:
        raw_after={str(f.relative_to(original)):digest(f) for f in sorted(original.rglob('*')) if f.is_file() and '.venv-m5-s2-c' not in f.parts and 'wheels' not in f.parts}
        result['original_data_immutable']=raw_before==raw_after
        result['formal_preserved']=driver.files(project/'.venv-m5')==json.loads((original/'formal-before.json').read_text())
        source=json.loads((original/'source-before.json').read_text())
        result['source_preserved']=source=={name:digest(repo/name) for name in source}
        result['own_current_child']=None if driver.CURRENT is None else driver.CURRENT.pid
        result['scientific_validity']='NOT_APPROVED/OPEN';result['formal_adoption']='NOT_APPROVED'
        driver.save(dest/'acceptance.json',result)
        assert result['original_data_immutable'] and result['formal_preserved'] and result['source_preserved']

if __name__=='__main__':main()
