"""UPSTREAM/PAPER citation receipts from pinned bytes, no source redistribution."""
import argparse
import ast
import hashlib
import json
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SDIST='8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec'


def main():
    p=argparse.ArgumentParser();p.add_argument('--sdist',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assert sha(a.sdist.read_bytes())==SDIST
    ledger=[]
    spans=[('py_src/Rbeast/beast.py','beast',1,45,'def beast'),
           ('py_src/Rbeast/beast.py','beast output contract',254,280,'.cpOccPr'),
           ('py_src/Rbeast/beast.py','beast prior/MCMC/extra/native call',420,503,'mcmc.burnin'),
           ('ext_src/glue_code.c','beast dispatch',150,174,'beast2_main_corev4'),
           ('ext_src/beastv2_COREV4.c','beast2_main_corev4 MCMC',285,390,'basis->Propose'),
           ('ext_src/beastv2_COREV4.c','proposal accept/store',513,625,'bStoreCurrentSample'),
           ('ext_src/beastv2_COREV4.c','knot tally',836,852,'xProb'),
           ('ext_src/beastv2_COREV4.c','posterior normalize',1124,1132,'inv_sample'),
           ('ext_src/beastv2_COREV4.c','trend cp output',1465,1540,'result.tcpPr'),
           ('ext_src/abc_common.c','FindChangepoint_LeftRightMargins',995,1052,'f32_sumfilter'),
           ('ext_src/abc_common.c','FindChangepoint_LeftRightMargins probability cap',1248,1264,'min(1.0'),
           ('ext_src/beastv2_io_in_args.c','GetArg_3rd_Prior native constraints',852,889,'trendMaxKnotNum'),
           ('ext_src/abc_rand_pcg_local_avx512.c','avx512_pcg_set_seed',88,111,'rng->increment')]
    with tarfile.open(a.sdist) as t:
        for path,function,start,end,anchor in spans:
            blob=t.extractfile('rbeast-0.1.25/'+path).read();lines=blob.decode('latin1').splitlines()
            span='\n'.join(lines[start-1:end]);assert anchor in span,(path,start,end)
            ledger.append(dict(nature='UPSTREAM',release='Rbeast0.1.25',sdist_sha256=SDIST,path=path,function=function,line_start=start,line_end=end,file_sha256=sha(blob),text_encoding='latin1 lossless byte mapping',span_normalized_lf_sha256=sha(span.encode()),anchor=anchor))
    for path,function,start,end in [('flash/rbeast_adapter.py','PARAMETERS',12,19),('flash/rbeast_adapter.py','candidates_from_raw',22,55),('flash/rbeast_adapter.py','RbeastAdapter/worker',75,125),('flash/change_detection.py','preprocess',28,54),('flash/change_detection.py','filter_candidates',57,104),('flash/change_detection.py','detect/prefix_replay',107,130)]:
        blob=(ROOT/path).read_bytes();span='\n'.join(blob.decode().splitlines()[start-1:end]);ledger.append(dict(nature='ADAPTATION',commit='d2973f5fa66ae99ec7ea09ea7040a11d1b95b845',path=path,function=function,line_start=start,line_end=end,file_sha256=sha(blob),span_normalized_lf_sha256=sha(span.encode())))
    text=(ROOT/'references/chapter3_extracted.txt').read_text();lines=text.splitlines()
    paper=[]
    for section,page,anchor in [('3.2.2',26,'FLASH 使用Rbeast'),('3.2.2',26,'计算每个时刻的运行长度'),('3.2.2',27,'recovery_ratio 定义'),('3.4.3',40,'持续超过20'),('3.4.4',43,'覆盖5% 到85%'),('3.4.5',44,'BOCD 变点检测通常引入1–2')]:
        hits=[i for i,line in enumerate(lines,1) if anchor in line];assert len(hits)==1,(anchor,hits)
        paper.append(dict(nature='PAPER',section=section,printed_page=page,original_pdf_page=page+16,chapter_pdf_page1=page-18,text_line=hits[0],anchor=anchor,line_sha256=sha(lines[hits[0]-1].encode())))
    tree=ast.parse((ROOT/'flash/rbeast_adapter.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='PARAMETERS' for x in n.targets))
    parameters={x.arg:ast.literal_eval(x.value) for x in node.value.keywords}
    result=dict(sdist_sha256=SDIST,release_url='https://pypi.org/project/rbeast/0.1.25/',upstream=ledger,paper=paper,
                paper_files={k:sha((ROOT/k).read_bytes()) for k in ['references/chapter3.pdf','references/chapter3_extracted.txt','SPEC.md']},
                parameters={k:dict(value=v,nature='ADAPTATION',paper_authority=False,upstream_contract='py_src/Rbeast/beast.py:beast',status='UNAPPROVED_MODEL_OR_ENGINEERING_CHOICE') for k,v in parameters.items()},
                full_pages_visually_reviewed=[26,27,40,43,44],license='packaged MIT; P1 third-party notice/redistribution issues still OPEN')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print('pinned source/parameter/paper receipts PASS')


if __name__=='__main__':main()
