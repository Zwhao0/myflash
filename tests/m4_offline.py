"""CLI fixture verification against committed independent hand expectations."""
import argparse
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def verify(actual,checks):
    for path,expected in checks.items():
        value=actual
        for part in path.split('.'):
            value=value[int(part)] if isinstance(value,list) else value[part]
        if type(expected) is float:
            assert math.isclose(value,expected,rel_tol=1e-10,abs_tol=1e-12),(path,value,expected)
        else:
            assert value==expected,(path,value,expected)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    results=[]
    for name in json.loads((ROOT/'tests/m4_cases/index.json').read_text()):
        fixture=ROOT/'tests/m4_cases'/name
        dest=a.output/name;dest.mkdir()
        expected=json.loads((fixture/'expected.json').read_text())
        command=[sys.executable,'scripts/m4_analyze.py','--input',str(fixture/'input.json'),'--output',str(dest/'actual.json')]
        if (fixture/'ingestion.json').exists():
            config=json.loads((fixture/'ingestion.json').read_text())
            command+=['--format',config['format'],'--records']+[str(fixture/x) for x in config['records']]
            if config.get('supplements'):command+=['--supplements',str(fixture/config['supplements'])]
        with (dest/'stdout.log').open('w') as f:
            r=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        (dest/'exit_code.txt').write_text(str(r.returncode)+'\n')
        try:
            assert r.returncode==expected['exit_code'],(r.returncode,expected['exit_code'])
            verify(json.loads((dest/'actual.json').read_text()),expected['checks'])
            status='PASS'
            reason=None
        except (AssertionError,KeyError,ValueError) as e:
            status='FAIL';reason=str(e)
        results.append(dict(fixture=name,status=status,reason=reason,command=command,exit_code=r.returncode,
            input=str(fixture/'input.json'),hand_expected=str(fixture/'expected.json'),actual=str(dest/'actual.json'),log=str(dest/'stdout.log')))
    summary=dict(machine=platform.node(),python=sys.version,status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',results=results)
    (a.output/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(status=summary['status'],fixtures=len(results),failures=[r for r in results if r['status']=='FAIL'])))
    return 0 if summary['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
