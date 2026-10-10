# ADAPTATION: host C++ build, pinned M1/M2 headers, no nvcc or kernel.
import hashlib,json,pathlib,subprocess,sys,datetime
root=pathlib.Path(__file__).resolve().parents[1]
out=root/"runs"/("m2-build-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
out.mkdir(parents=True);build=root/"build";build.mkdir(exist_ok=True)
site=root/".venv-m1/lib/python3.12/site-packages"
includes=[site/"nvidia/nccl/include",site/"nvidia/cuda_runtime/include",site/"triton/backends/nvidia/include",root/".build-deps-m2/nvidia/cuda_cccl/include"]
checks=[site/"nvidia/nccl/include/nccl.h",site/"triton/backends/nvidia/include/crt/host_config.h",includes[-1]/"nv/target"]
if not all(p.is_file() for p in checks): raise SystemExit("Missing approved build headers")
base=["g++","-std=c++17","-O2","-g","-fPIC","-shared","-pthread","-Wall","-Wextra","-Wno-unused-parameter",*["-I"+str(p) for p in includes]]
commands=[
 base+[str(root/"tests/m2_mock_nccl.cpp"),"-Wl,-z,defs","-o",str(build/"libm2_mock_nccl.so")],
 base+[str(root/"tests/m2_lifecycle_driver.cpp"),"-L"+str(site/"nvidia/nccl/lib"),"-l:libnccl.so.2","-Wl,-rpath,"+str(site/"nvidia/nccl/lib"),"-o",str(build/"libm2_lifecycle_driver.so")],
 base+[str(root/"native/ring.cpp"),str(root/"native/probe.cpp"),"-Wl,-z,defs","-ldl","-lcrypto","-o",str(build/"libflash_probe.so")],
 base+[str(root/"native/ring.cpp"),"-Wl,-z,defs","-o",str(build/"libflash_reader.so")],
 base+["-DFLASH_RING_TESTING",str(root/"native/ring.cpp"),"-Wl,-z,defs","-o",str(build/"libflash_ring_test.so")],
]
records=[]
for index,cmd in enumerate(commands):
 p=subprocess.run(cmd,text=True,capture_output=True,cwd=root)
 (out/f"{index}.log").write_text(p.stdout+p.stderr)
 records.append(dict(command=cmd,exit_code=p.returncode,log=str(out/f"{index}.log")))
 if p.returncode:break
manifest=dict(host=__import__("socket").gethostname(),commands=records,header_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checks},source_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/"native").glob("*") if p.is_file()},outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in build.glob("libflash*.so")})
(out/"manifest.json").write_text(json.dumps(manifest,indent=2))
print(json.dumps(dict(exit_code=records[-1]["exit_code"],run_dir=str(out))))
if records[-1]["exit_code"]:print((out/f"{len(records)-1}.log").read_text())
sys.exit(records[-1]["exit_code"])
