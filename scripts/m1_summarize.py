"""ADAPTATION: export allow-listed M1 evidence, never raw NCCL/topology/UUID data."""
import argparse,json,re,statistics,subprocess
from pathlib import Path


def summarize(root):
    results=[]
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True,timeout=10).splitlines()
    active={s.strip() for s in active}
    for p in sorted((root/'runs').glob('m1[bcd]-*/node-*')):
        if not (p/'manifest.json').exists():continue
        m=json.loads((p/'manifest.json').read_text())
        records=[json.loads(f.read_text()) for f in sorted(p.glob('rank-*.json'))]
        entries=[]
        for d in records:
            fields=['status','mode','rank','local_rank','world_size','steps','torch','torch_build_cuda','collectives_checked','initial_expected_sum','dtype','peak_allocated_bytes','peak_reserved_bytes','own_process_memory_mib','memory_target_mib','memory_target_exceeded','parameter_count','max_parameter_delta','max_final_sync_error','final_loss','parallel_groups','moe','process_group_destroyed','rows']
            e={k:d[k] for k in fields if k in d}
            normalize=lambda s:s.lower().removeprefix('gpu-').replace('-','')
            e['uuid_mapping_verified']=normalize(d.get('gpu_uuid','?'))==normalize(d.get('cuda_uuid','!'))
            e['process_absent_from_gpu_after_exit']=str(d['pid']) not in active
            e['runtime_versions']=[dict(family=x['family'],encoded=x['encoded'],library=Path(x['path']).name) for x in d.get('runtime',{}).get('versions',[])]
            if d.get('error'):e['failure_category']='resource_budget' if 'budget' in d['error'] else 'see private rank log'
            entries.append(e)
        lines=[line for f in p.glob('nccl.*.log') for line in f.read_text().splitlines()]
        net=dict(p2p_channel_lines=sum('via P2P' in x for x in lines),using_network_ib=any('Using network IB' in x for x in lines),roce_label=any('RoCE' in x for x in lines),net_ib_channel_lines=sum('via NET/IB' in x for x in lines),net_socket_channel_lines=sum('via NET/Socket' in x for x in lines),gdr_channel_lines=sum('via NET/IB' in x and 'GDR' in x for x in lines))
        gpu_rows=[x.split(',') for x in (p/'gpu-preflight.log').read_text().splitlines()]
        startup_free=[float(x[1])-float(x[2]) for x in gpu_rows if x[0].strip() in m['gpus']]
        results.append(dict(startup_min_free_mib=min(startup_free),run_id=m['run_id'],node_rank=m['node_rank'],source_commit=m['source_commit'],source_hashes=m['source_hashes'],source_diff_sha256=m['source_diff_sha256'],status=m['status'],exit_code=m['exit_code'],elapsed_s=m['elapsed_s'],remaining_own_process_count=len(m['remaining_own_pids']),network=net,ranks=entries))
    return dict(schema=1,scope='M1 native NCCL/DDP, no FLASH, no fault injection',runs=results)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=summarize(Path(__file__).resolve().parents[1]);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,indent=2)+'\n')
    print('SUMMARIZED_NODE_RUNS',len(data['runs']))
