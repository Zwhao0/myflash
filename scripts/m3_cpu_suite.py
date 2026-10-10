# ADAPTATION: complete CPU command/exit/log manifest.
import datetime,json,subprocess,socket,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'runs'/('m3-cpu-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
commands=[['python3',x] for x in ['scripts/m3_build.py','tests/m2_ring.py','tests/m2_hook_smoke.py','tests/m3_reader.py','tests/m3_hook.py','tests/m3_validation.py']]
results=[]
for i,cmd in enumerate(commands):
 with (out/f'{i}.log').open('w') as f:r=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(command=cmd,exit_code=r.returncode,log=str(out/f'{i}.log')))
 if r.returncode:break
(out/'manifest.json').write_text(json.dumps(dict(host=socket.gethostname(),commands=results,status='PASS' if len(results)==len(commands) and all(x['exit_code']==0 for x in results) else 'FAIL'),indent=2))
print(json.dumps(dict(directory=str(out),exits=[x['exit_code'] for x in results])));sys.exit(results[-1]['exit_code'])
