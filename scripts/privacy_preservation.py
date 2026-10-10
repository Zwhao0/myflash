import ast, hashlib, json, subprocess
from pathlib import Path
root=Path.cwd();base='2fcc45724e8bbfde800539beeae45febddd7e572'
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',base],text=True).splitlines()
checked=[]
for name in paths:
 if name.startswith(('native/','flash/','scripts/','tests/')) and name!='scripts/m1_inventory.py' or name.endswith('.csv') or name.startswith(('docs/m1/','docs/m2/','docs/m3/')) and name.endswith('.json') and name!='docs/m3/SYNC.json' or name.startswith('references/'):
  old=subprocess.check_output(['git','show',base+':'+name]);new=(root/name).read_bytes()
  assert old==new,name
  checked.append({'path':name,'sha256':hashlib.sha256(new).hexdigest()})
for name in subprocess.check_output(['git','ls-files'],text=True).splitlines():
 if name.endswith('.json'):json.loads((root/name).read_text())
module=ast.parse((root/'scripts/m1_inventory.py').read_text())
assignment=next(n for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='root' for t in n.targets))
expression=ast.Expression(assignment.value);ast.fix_missing_locations(expression)
resolved=eval(compile(expression,'<root-expression>','eval'),{'Path':Path,'__file__':str(root/'scripts/m1_inventory.py')})
assert resolved==root.resolve()
print(json.dumps({'status':'PASS','unchanged_files':len(checked),'json_parse':'PASS','inventory_root_expression':'PASS','hashes':checked},indent=2))
