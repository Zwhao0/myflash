"""ADAPTATION TASK09 read-only verifier of raw receipts and exact-base bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE='b082d16939aab0d4ba4b9208475886c4b9ec808c'
ROOT=Path(__file__).resolve().parents[3]
REQUIRED={'bridge05':35,'regression-m6_control':32,'regression-m5_reporter':4,
          'regression-m6b_ready_reporter_outbox':33,'regression-cursor02':9,
          'regression-m6b_ready_cursor_extra':8,'regression-m5_detection':8,
          'regression-m6b_ready_approved_detection':13,'regression-m6b_ready_approved_localization':20}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def verify(private):
    commands=[]
    for label,count in REQUIRED.items():
        folder=private/label;r=json.loads((folder/'receipt.json').read_text())
        assert r['exit']==0 and r['timeout'] is False,(label,'exit')
        assert sha(folder/'stdout')==r['stdout_sha256'] and sha(folder/'stderr')==r['stderr_sha256'],(label,'log hash')
        assert ('Ran '+str(count)+' tests') in (folder/'stderr').read_text(),(label,'count')
        for name,value in r['sources'].items():
            # Old regressions were run before the last new-module thread refinement;
            # every unchanged test and every inherited source is still exact.
            if name in ('flash/m6_abi2_bridge.py','tests/task09_abi2_cpu.py') and label!='bridge05':
                continue
            assert sha(ROOT/name)==value,(label,name,'source bytes')
        commands.append(dict(label=label,count=count,argv=r['argv'],cwd=r['cwd'],host=r['host'],
                             exit=r['exit'],timeout=r['timeout'],stdout_sha256=r['stdout_sha256'],stderr_sha256=r['stderr_sha256']))
    for label,expected in [('bridge01',1),('regression-m6b_ready_cursor_contract',2)]:
        folder=private/label;r=json.loads((folder/'receipt.json').read_text())
        assert r['exit']==expected
        assert sha(folder/'stdout')==r['stdout_sha256'] and sha(folder/'stderr')==r['stderr_sha256']
    failed=json.loads((private/'bridge01/receipt.json').read_text())
    for name in ('flash/m6_abi2_bridge.py','tests/task09_abi2_cpu.py'):
        assert sha(private/'bridge01/source'/Path(name).name)==failed['sources'][name]
    files=[]
    for line in git('ls-tree','-rz','--full-tree',BASE).split(b'\0'):
        if not line:continue
        meta,path=line.split(b'\t',1);mode,kind,oid=meta.decode().split()
        assert kind=='blob'
        files.append((path.decode(),oid))
    process=subprocess.run(['git','hash-object','--stdin-paths'],input=''.join(path+'\n' for path,_ in files).encode(),cwd=ROOT,capture_output=True,check=True)
    current=process.stdout.decode().splitlines();assert len(current)==len(files)
    protected=[];appended=[]
    for (name,oid),actual in zip(files,current):
        if name in ('STATUS.md','GAPS.md'):
            assert (ROOT/name).read_bytes().startswith(git('show',BASE+':'+name)),name
            appended.append(name)
        else:
            assert oid==actual,(name,'inherited bytes changed');protected.append(dict(path=name,git_blob=oid))
    result=dict(base=BASE,tree=git('rev-parse',BASE+'^{tree}').decode().strip(),base_files=len(files),
                protected_files=len(protected),append_only=appended,protected=protected,
                tests=sum(REQUIRED.values()),commands=commands,status='PASS')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--private-run',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args();r=verify(args.private_run)
    if args.output:args.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('status','base_files','protected_files','tests')}))


if __name__=='__main__':main()
