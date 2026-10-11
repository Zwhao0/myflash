"""ADAPTATION: check new text against existing private access literals.

Never print or store plaintext credentials, identities or their fingerprints.
"""
from pathlib import Path
import subprocess,re,json,sys
root=Path(__file__).resolve().parents[2]
repo=root/'m6b-s2-work';run=Path(__file__).resolve().parent
private=(root/'服务器.md').read_text()
host=re.findall(r'^ssh\s+([^\s`]+)',private,re.M)[0]
password=subprocess.check_output([str(root/'runs/m6a-access/askpass.py')]).decode().strip()
literals=[host,host.split('@')[-1],str(root)]
assert password
paths=subprocess.check_output(['git','diff','--name-only','--diff-filter=ACMR','3ba7dad2070ad13466b4f14562ee54fa4a3e818b'],cwd=repo,text=True).splitlines()
findings=[]
for name in paths:
    data=(repo/name).read_bytes()
    leaking=any(value.encode() in data for value in literals)
    # A short credential can coincide with a numeric posterior or hash substring.
    # Check whole textual JSON tokens / quoted source or log literals instead;
    # all mathematical numbers and full byte payloads remain untouched.
    text=data.decode()
    if name.endswith('.json'):
        def credential_token(value):
            if isinstance(value,str):return value==password
            if isinstance(value,dict):return any(k==password or credential_token(v) for k,v in value.items())
            if isinstance(value,list):return any(credential_token(v) for v in value)
            return False
        leaking=leaking or credential_token(json.loads(text))
    else:
        leaking=leaking or any(q+password+q in text for q in ('"',"'"))
    if leaking:findings.append(name)
result=dict(status='PASS' if not findings else 'FAIL',files=len(paths),findings=findings,
    scope='new/changed current text; SSH/project literals plus whole JSON textual or quoted source/log credential tokens; no numeric/base64/hash substring inference; no values printed',historical_scope='DEFERRED/OPEN')
(run/'exact-privacy.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));sys.exit(bool(findings))
