"""ADAPTATION CPU prefix replay. Reads records only, no evaluator truth."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.iteration_reporter import IterationRecord
from flash.change_detection import prefix_replay


def replay(path):
    raw=json.loads(path.read_text())
    try:
        if raw.get('schema')!=1:raise ValueError('invalid schema')
        records=[IterationRecord(**r) for r in raw['records']]
    except (ValueError,TypeError,KeyError) as error:
        return dict(input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),input=raw,
                    decisions=[dict(status='INVALID_INPUT',reason=str(error),final_alert=False)])
    return dict(input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                decisions=prefix_replay(records))


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    files=sorted(a.input.glob('*.json')) if a.input.is_dir() else [a.input]
    if not files:p.error('no input files')
    a.output.mkdir(parents=True,exist_ok=False)
    blocked=False
    for path in files:
        result=replay(path);dest=a.output/(path.stem+'.json')
        dest.write_text(json.dumps(result,allow_nan=False,indent=2)+'\n')
        states=[r['status'] for r in result['decisions']]
        blocked|='BLOCKED' in states
        print(json.dumps(dict(input=path.name,output=dest.name,decisions=len(states),states=sorted(set(states)))))
    return 77 if blocked else 0

if __name__=='__main__':raise SystemExit(main())
