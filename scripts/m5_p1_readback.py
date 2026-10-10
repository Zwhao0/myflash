"""ADAPTATION: independent standard-library public transport/byte audit.

This verifies exported artifacts, not native numerical correctness or a GPU run.
Run after regenerating data-index.json; never rewrite measurement evidence.
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import platform
import re


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=Path('docs/m5/patch-p1'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.evidence
    index=json.loads((root/'data-index.json').read_text())
    arrays={name:0 for name in ('m5-p1-b-batch01','m5-p1-c-batch01','m5-p1-c-batch02','m5-p1-b-batch02')}
    dtypes=set();size=0
    def walk(value,run):
        if isinstance(value,dict):
            if 'bytes_base64' in value:
                data=base64.b64decode(value['bytes_base64'],validate=True)
                assert hashlib.sha256(data).hexdigest()==value['sha256']
                dtype=value['dtype'];match=re.fullmatch(r'[<>=|][biufc](\d+)',dtype)
                assert match,dtype
                assert all(type(n) is int and n>=0 for n in value['shape'])
                assert len(data)==math.prod(value['shape'])*int(match.group(1))
                dtypes.add(dtype);arrays[run]+=1
            for child in value.values():walk(child,run)
        elif isinstance(value,list):
            for child in value:walk(child,run)
    for item in index['files']:
        path=Path(item['path']);assert not path.is_absolute() and '..' not in path.parts
        data=(root/path).read_bytes();size+=len(data)
        assert len(data)==item['size'] and hashlib.sha256(data).hexdigest()==item['sha256'],str(path)
        if len(path.parts)==3 and path.parts[0]=='data' and path.parts[1] in arrays and (
            path.name.startswith('reference-') or path.name.startswith('decisions-')):
            walk(json.loads(data),path.parts[1])
    assert all(n==132960 for n in arrays.values()),arrays
    result=dict(status='PASS',machine='local macOS arm64',python=platform.python_version(),
        files=len(index['files']),bytes=size,arrays_by_batch=arrays,arrays=sum(arrays.values()),
        dtypes=sorted(dtypes),native_experiment=False,gpu_experiment=False,
        note='Independent file SHA256, lossless base64, ndarray byte counts; node-0 native/comparator gates reported separately.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
