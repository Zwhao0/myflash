"""UPSTREAM Rbeast0.1.25 rb.beast; ADAPTATION bounded native subprocess.
Not Adams–MacKay incremental run-length BOCD. No GreyHound code copied.
"""
import importlib.metadata
import json
import math
import subprocess
import sys
from pathlib import Path

# ADAPTATION explicit experimental model, not paper-approved Rbeast parameters.
PARAMETERS = dict(start=1, deltat=1, season='none', method='bayes',
                  tcp_minmax=[0, 10], torder_minmax=[0, 1],
                  tseg_minlength=1, tseg_leftmargin=0, tseg_rightmargin=0,
                  mcmc_seed=20261010, mcmc_burbin=200, mcmc_chains=3,
                  mcmc_thin=5, mcmc_samples=8000, precValue=1.5,
                  precPriorType='componentwise', hasOutlier=False,
                  print_param=True, print_progress=False, print_warning=True,
                  quiet=False, gui=False, dump_ci=False, dump_mcmc=False)


def candidates_from_raw(raw, size):
    """cp is time coordinate with start1/deltat1, not a Python index.
    cpPr pairs with cp; cpOccPr is a different full-time occurrence posterior.
    Keep padded slots and explicit validation reasons. Never truncate to ncp_mode.
    """
    if not isinstance(raw, dict) or not isinstance(raw.get('trend'), dict):
        raise ValueError('missing trend result')
    trend = raw['trend']
    cp, probability, occurrence = [trend.get(k) for k in ('cp', 'cpPr', 'cpOccPr')]
    if not all(isinstance(x, list) for x in (cp, probability, occurrence)):
        raise ValueError('missing candidate/probability arrays')
    if len(cp) != len(probability) or len(occurrence) != size:
        raise ValueError('result shape mismatch')
    for x in occurrence:
        if type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1:
            raise ValueError('invalid cpOccPr')
    result=[];seen=set()
    for slot, (coordinate, prob) in enumerate(zip(cp, probability)):
        row=dict(slot=slot, cp=coordinate, cpPr=prob, index0=None, reason=None)
        if coordinate is None and prob is None:
            row['reason']='PADDED_SLOT'
        elif (type(coordinate) not in (int, float) or not math.isfinite(coordinate) or
              coordinate != int(coordinate) or not 1 <= coordinate <= size):
            row['reason']='INVALID_COORDINATE'
        elif type(prob) not in (int,float) or not math.isfinite(prob) or not 0 <= prob <= 1:
            row['reason']='INVALID_PROBABILITY'
        elif int(coordinate) in seen:
            row['reason']='DUPLICATE_COORDINATE'
        else:
            row['index0']=int(coordinate)-1
            row['cpOccPr_at_coordinate']=occurrence[row['index0']]
            seen.add(int(coordinate))
        result.append(row)
    return result


def json_safe(value):
    """Preserve full native output tree; NaN padding -> explicit JSON null."""
    if hasattr(value, 'tolist'):
        return json_safe(value.tolist())
    if isinstance(value, dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):
        return [json_safe(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value,(str,int,float,bool)):
        return value
    if hasattr(value,'__dict__'):
        return json_safe(vars(value))
    raise ValueError('unsupported native output type')


class RbeastAdapter:
    def __init__(self, timeout_s=30):
        self.timeout_s=timeout_s

    def analyze(self, values):
        evidence=dict(engine='Rbeast.beast', semantics='retrospective-window-refit',
                      parameters=PARAMETERS, probability_field='trend.cpPr',
                      probability_meaning='BEAST localized changepoint occurrence posterior; not P(run_length=0)',
                      coordinate='start=1/deltat=1 time; Python index=cp-1',
                      scientific_status='AMBIGUOUS_SPEC', raw=None)
        try:
            command=[sys.executable,str(Path(__file__).resolve()),'--worker']
            run=subprocess.run(command,input=json.dumps(values,allow_nan=False),
                               text=True,capture_output=True,timeout=self.timeout_s)
            evidence.update(worker_exit_code=run.returncode, native_stdout=run.stdout,
                            native_stderr=run.stderr)
            lines=[line[len('M5_RESULT='):] for line in run.stdout.splitlines() if line.startswith('M5_RESULT=')]
            if run.returncode or len(lines)!=1:
                evidence.update(status='BLOCKED' if run.returncode==77 else 'INSUFFICIENT_EVIDENCE',reason='NATIVE_WORKER_FAILED')
                return evidence
            payload=json.loads(lines[0]);evidence.update(payload)
            evidence['candidates']=candidates_from_raw(evidence['raw'],len(values))
            invalid=[r for r in evidence['candidates'] if r['reason'] not in (None,'PADDED_SLOT')]
            evidence.update(status='INSUFFICIENT_EVIDENCE' if invalid else 'OK',reason='INVALID_NATIVE_CANDIDATE' if invalid else None)
        except subprocess.TimeoutExpired as error:
            evidence.update(status='INSUFFICIENT_EVIDENCE',reason='NATIVE_TIMEOUT',
                            native_stdout=(error.stdout or b'').decode(errors='replace') if isinstance(error.stdout,bytes) else error.stdout)
        except (ValueError,TypeError,KeyError,OSError) as error:
            evidence.update(status='INSUFFICIENT_EVIDENCE',reason=type(error).__name__+': '+str(error))
        return evidence


def worker():
    try:
        import numpy as np
        import Rbeast as rb
    except ImportError as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr)
        return 77
    if importlib.metadata.version('Rbeast')!='0.1.25' or np.__version__!='2.2.6':
        raise RuntimeError('unverified Rbeast/NumPy version')
    values=json.load(sys.stdin)
    out=rb.beast(np.asarray(values,dtype=np.float64),**PARAMETERS)
    payload=dict(raw=json_safe(out),versions=dict(Rbeast=importlib.metadata.version('Rbeast'),numpy=np.__version__,python=sys.version))
    print('M5_RESULT='+json.dumps(payload,allow_nan=False))
    return 0

if __name__=='__main__':
    if sys.argv[1:]!=['--worker']:raise SystemExit('only --worker supported')
    raise SystemExit(worker())
