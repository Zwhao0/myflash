"""ADAPTATION: assert the installed C instance, without a native fit."""
import argparse
import base64
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--environment',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import numpy as np
    import Rbeast as rb
    expected=a.environment.absolute()
    assert Path(sys.prefix)==expected and Path(sys.executable).absolute().is_relative_to(expected)
    assert sys.version_info[:3]==(3,12,3)
    assert np.__version__=='2.2.6' and importlib.metadata.version('Rbeast')=='0.1.25'
    for module in (np,rb):assert Path(module.__file__).absolute().is_relative_to(expected)
    native=list(Path(rb.__file__).parent.glob('Rbeast*.so'));assert len(native)==1
    assert digest(native[0])=='1f08fbc9f24d0c00eb21f91f357519f15289ffd1ef18b9e7e0aca47c2596faeb'
    records={}
    for name in ('Rbeast','numpy'):
        dist=importlib.metadata.distribution(name);record=dist.read_text('RECORD');checked=0
        for name_,h,size in csv.reader(record.splitlines()):
            file=Path(dist.locate_file(name_));assert file.resolve().is_relative_to(expected)
            if h:
                algorithm,value=h.split('=',1);data=file.read_bytes()
                assert base64.urlsafe_b64encode(hashlib.new(algorithm,data).digest()).decode().rstrip('=')==value
                assert not size or int(size)==len(data);checked+=1
        records[name]=dict(version=dist.version,record_sha256=hashlib.sha256(record.encode()).hexdigest(),checked_members=checked)
    maps=[line for line in Path('/proc/self/maps').read_text().splitlines() if str(native[0]) in line]
    assert maps,'Candidate .so was not actually mapped'
    result=dict(sys_executable=sys.executable,sys_prefix=sys.prefix,python=sys.version,
        interpreter_sha256=digest(Path(sys.executable).resolve()),Rbeast_file=rb.__file__,numpy_file=np.__file__,
        native_file=str(native[0]),native_sha256=digest(native[0]),mapped_library_lines=maps,
        versions=records,pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)),
        priority_nice=os.getpriority(os.PRIO_PROCESS,0),status='PASS_IDENTITY_NOT_FIT')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Installed C interpreter/module/native map/RECORD identity PASS')

if __name__=='__main__':main()
