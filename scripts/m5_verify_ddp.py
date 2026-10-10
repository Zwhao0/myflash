"""ADAPTATION paired opt-in DDP audit. Reads training only, no fault truth."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.iteration_reporter import LocalHistory
from flash.change_detection import prefix_replay


def main():
    p=argparse.ArgumentParser();p.add_argument('--off',type=Path,required=True);p.add_argument('--on',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    evidence=dict(status='FAIL',ranks=[],raw_detector_rank0=None)
    for rank in range(2):
        off=json.loads((a.off/f'rank-{rank}.json').read_text());on=json.loads((a.on/f'rank-{rank}.json').read_text())
        assert off['status']==on['status']=='PASS'
        assert on['process_group_destroyed'] and off['process_group_destroyed']
        assert on['final_parameters']==off['final_parameters']
        for x,y in zip(off['rows'],on['rows']):
            assert x['loss']==y['loss'] and x['gradient_sha256']==y['gradient_sha256']
            assert x['max_gradient_sync_error']<=1e-6 and y['max_gradient_sync_error']<=1e-6
            assert x['max_parameter_sync_error']<=1e-6 and y['max_parameter_sync_error']<=1e-6
        history=LocalHistory.load(a.on/f'iterations-rank-{rank}.json')
        assert len(history)==20 and [r.iteration for r in history]==list(range(1,21))
        assert all(r.global_rank==rank and r.cuda_completion_wait for r in history)
        evidence['ranks'].append(dict(rank=rank,records=len(history),loss=[r['loss'] for r in on['rows']],gradient_sha256=[r['gradient_sha256'] for r in on['rows']],iteration_ms=[r.iteration_time_ms for r in history],final_parameter_sha256=hashlib.sha256(json.dumps(on['final_parameters']).encode()).hexdigest(),delta=on['max_parameter_delta'],sync_error=on['max_final_sync_error'],own_memory_mib=on['own_process_memory_mib']))
        if rank==0:evidence['raw_detector_rank0']=prefix_replay(history)
    evidence['status']='PASS';a.output.write_text(json.dumps(evidence,indent=2)+'\n')
    print('paired numerical equality and completed records PASS')

if __name__=='__main__':main()
