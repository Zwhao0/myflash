"""ADAPTATION: execute unchanged strict replay assertion; retain its globals.

No assertion/exception is suppressed: finally captures full/short evidence and
the original exception propagates with its real nonzero interpreter exit.
"""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'tests/m5_replay.py'
capture=Path(sys.argv[1])
sys.argv=[str(source),*sys.argv[2:]]
namespace=dict(__name__='__main__',__file__=str(source))
try:
    exec(compile(source.read_bytes(),str(source),'exec'),namespace)
finally:
    evidence={k:namespace[k] for k in ('full','short') if k in namespace}
    capture.write_text(json.dumps(evidence,allow_nan=False)+'\n')
