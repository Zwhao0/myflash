"""PAPER window/means/recovery; ADAPTATION validation and full audit evidence.
Task05 approved G01-a/G02-inclusive/G13-A rules require explicit opt-in.
The legacy default remains unchanged; G20 final system alerts remain unavailable.
"""
import math
import statistics
from dataclasses import asdict, dataclass
from .iteration_reporter import validate_sequence
from .rbeast_adapter import RbeastAdapter, candidates_from_raw, PARAMETERS


# ADAPTATION: owner approval in task05, anchored to the reviewed task04 packet.
APPROVED_RULES_VERSION = 'flash.detection.approved.v1'
APPROVED_PACKET_HEAD = '5f9cccf2c8582837ba1050fafdf7f56106964465'


@dataclass(frozen=True)
class DetectionConfig:
    window: int = 30
    thresh_prob: float = 0.8
    degradation_thresh: float = 0.2
    warmup: int = 3
    zscore: float = 3.0
    spacing: int = 2
    recovery: float = 0.75

    def __post_init__(self):
        # M5 has no authorization to tune paper constants for results.
        if asdict(self) != dict(window=30,thresh_prob=0.8,degradation_thresh=0.2,
                               warmup=3,zscore=3.0,spacing=2,recovery=0.75):
            raise ValueError('M5 paper constants are fixed')


def preprocess(records, config):
    validate_sequence(records)
    if any(r.global_rank != 0 for r in records):
        raise ValueError('detector input must be rank0')
    window=records[-config.window:]
    eligible=[r for r in window if r.iteration>config.warmup]
    values=[r.iteration_time_ms for r in eligible]
    mean=statistics.fmean(values) if values else None
    std=statistics.pstdev(values) if values else None
    sample_std=statistics.stdev(values) if len(values)>1 else None
    kept=[];stages=[]
    for record in window:
        warm=record.iteration<=config.warmup
        z=None if warm else 0.0 if std==0 else abs((record.iteration_time_ms-mean)/std)
        sample_z=0.0 if sample_std==0 else abs((record.iteration_time_ms-mean)/sample_std) if sample_std and not warm else None
        reason='WARMUP' if warm else 'ZSCORE_OUTLIER' if z>config.zscore else None
        index=None
        if reason is None:index=len(kept);kept.append(record)
        stages.append(dict(iteration=record.iteration,time_ms=record.iteration_time_ms,
                           warmup_removed=warm,zscore_population=z,zscore_sample=sample_z,
                           threshold=config.zscore,filtered_index0=index,reason=reason))
    return dict(window_iterations=[r.iteration for r in window], stages=stages,
                mean_ms=mean,population_std_ms=std,sample_std_ms=sample_std,
                index0_to_iteration=[r.iteration for r in kept],
                iteration_to_index0={str(r['iteration']):r['filtered_index0'] for r in stages},
                values_ms=[r.iteration_time_ms for r in kept],
                temporal_semantics='compressed retained samples; original iteration mapping preserved')


def filter_candidates(prepared, candidates, latest, config, *, approved_rules=False):
    if type(approved_rules) is not bool:
        raise ValueError('approved_rules must be an explicit bool')
    if approved_rules:
        return _filter_approved_candidates(prepared, candidates, latest, config)
    values=prepared['values_ms'];mapping=prepared['index0_to_iteration']
    result=[];previous=None
    # Returned cp usually ordered by importance, not chronology.
    for candidate in sorted(candidates,key=lambda c:(c['index0'] is None,c['index0'] or 0,c['slot'])):
        row=dict(candidate);row.update(iteration=None,stages={},status='SKIPPED',reason=candidate.get('reason'))
        if row['reason']:
            result.append(row);continue
        i=candidate['index0'];iteration=mapping[i];row['iteration']=iteration
        probability_pass=candidate['cpPr']>=config.thresh_prob
        row['stages']['probability']=dict(value=candidate['cpPr'],threshold=config.thresh_prob,comparison='>=',passed=probability_pass,field='trend.cpPr',assumption='G01 interpretation unresolved')
        distance=None if previous is None else iteration-previous
        distance_pass=distance is None or distance>=config.spacing
        row['stages']['spacing']=dict(original_iteration_distance=distance,threshold=config.spacing,passed=distance_pass,reference='previous probability-qualified chronological candidate')
        if probability_pass and distance_pass:previous=iteration
        left,right,recent=values[:i],values[i:],values[i+1:]
        baseline=statistics.fmean(left) if left else None
        degraded=statistics.fmean(right) if right else None
        recent_mean=statistics.fmean(recent) if recent else None
        stats=dict(baseline_mean=baseline,degraded_mean=degraded,recent_mean=recent_mean,
                   left_sample_count=len(left),right_sample_count=len(right),recent_sample_count=len(recent),
                   observed_original_iterations=latest-iteration+1,
                   observed_duration_gt20=latest-iteration+1>20,
                   mean_slices='whole filtered window: [:cp], [cp:], [cp+1:]; latest included')
        row['statistics']=stats
        delta=None if baseline is None or degraded is None else degraded-baseline
        duration_ratio=None if not baseline else delta/baseline
        throughput_loss=None if not degraded or delta is None else delta/degraded
        row['stages']['degradation']=dict(duration_growth=duration_ratio,throughput_loss=throughput_loss,
              threshold=config.degradation_thresh,duration_growth_pass=None if duration_ratio is None else duration_ratio>config.degradation_thresh,
              throughput_loss_pass=None if throughput_loss is None else throughput_loss>config.degradation_thresh,
              comparison='>',approved_formula=None,reason='G13 denominator/direction unspecified')
        recovery=None if not left or not recent or delta==0 else (degraded-recent_mean)/delta
        row['stages']['recovery']=dict(value=recovery,threshold=config.recovery,
              filtered=None if recovery is None else recovery>=config.recovery,
              denominator_ms=delta,reason='INSUFFICIENT_SAMPLES_OR_ZERO_DENOMINATOR' if recovery is None else None)
        row['stages']['persistence']=dict(required_iterations=None,observed_original_iterations=latest-iteration+1,decision=None,reason='G02 >20 versus 1–2 unresolved')
        if not probability_pass:row['reason']='PROBABILITY_BELOW_THRESHOLD'
        elif not distance_pass:row['reason']='ADJACENT_CHANGEPOINT'
        elif recovery is None:row.update(status='INSUFFICIENT_EVIDENCE',reason='INSUFFICIENT_SAMPLES_OR_ZERO_DENOMINATOR')
        elif recovery>=config.recovery:row['reason']='TRANSIENT_RECOVERY'
        elif delta<=0:row['reason']='NO_DURATION_INCREASE'
        else:
            row.update(status='AMBIGUOUS_SPEC',reason='G01_G02_G13_UNAPPROVED_FINAL_RULE',
                       provisional_duration_candidate=duration_ratio>config.degradation_thresh,
                       provisional_throughput_candidate=throughput_loss>config.degradation_thresh)
        result.append(row)
    return result


def _positive_finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _filter_approved_candidates(prepared, candidates, latest, config):
    """ADAPTATION G01 contract steps8-12; PAPER thresholds; G02/G13 owner choices.

    Reuse the exact reviewed means, chronology and spacing-before-recovery order.
    No state pins an old candidate or baseline across rolling-window refits.
    """
    values = prepared['values_ms']
    mapping = prepared['index0_to_iteration']
    if (type(latest) is not int or latest < 1 or not values or len(values) != len(mapping)
            or any(not _positive_finite(v) for v in values)
            or any(type(j) is not int or not 1 <= j <= latest for j in mapping)
            or any(a >= b for a, b in zip(mapping, mapping[1:]))):
        raise ValueError('invalid filtered values or original iteration mapping')
    seen = set()
    for c in candidates:
        if (c.get('reason') == 'PADDED_SLOT' and c.get('cp') is None
                and c.get('cpPr') is None and c.get('index0') is None):
            continue
        i = c.get('index0')
        if (c.get('reason') is not None or type(i) is not int or not 0 <= i < len(values)
                or type(c.get('cp')) not in (int, float) or c['cp'] != i + 1
                or type(c.get('cpPr')) not in (int, float) or not math.isfinite(c['cpPr'])
                or not 0 <= c['cpPr'] <= 1 or type(c.get('slot')) is not int
                or c['slot'] < 0 or i in seen):
            raise ValueError('invalid native candidate')
        seen.add(i)
    try:
        rows = filter_candidates(prepared, candidates, latest, config)
    except ArithmeticError:
        # ADAPTATION G13: numerical overflow is insufficient evidence, never healthy.
        return [dict(c, iteration=mapping[c['index0']] if c['index0'] is not None else None,
            stages={}, status='INSUFFICIENT_EVIDENCE', reason='CANDIDATE_ARITHMETIC_FAILED',
            model_candidate=c['index0'] is not None, qualified_candidate=False,
            detection_trigger=False, final_alert=False) for c in candidates]
    for row in rows:
        row.update(model_candidate=row['reason'] != 'PADDED_SLOT',
                   qualified_candidate=False, detection_trigger=False, final_alert=False)
        row.pop('provisional_duration_candidate', None)
        row.pop('provisional_throughput_candidate', None)
        if row['reason'] == 'PADDED_SLOT':
            continue
        stages = row['stages']
        stages['probability']['assumption'] = 'APPROVED_G01_a_FINITE_WINDOW_BEAST_ONLY'
        stages['degradation'].update(approved_formula='A', reason=None,
                                    measured_throughput=None,
                                    measured_throughput_reason='NOT_MEASURED_WORK_AND_WALLTIME',
                                    throughput_loss_role='DIAGNOSTIC_FIXED_WORK_PROXY_ONLY')
        span = latest - row['iteration'] + 1
        stages['persistence'] = dict(rule='inclusive_span', required_iterations=21,
            observed_original_iterations=span, comparison='t-j+1>20',
            decision=span > 20, reason=None,
            meaning='current candidate age; not continuous physical degradation')
        stats = row['statistics']
        arithmetic_valid = (all(_positive_finite(stats[k]) for k in
                ('baseline_mean', 'degraded_mean', 'recent_mean'))
            and all(type(v) in (int, float) and math.isfinite(v) for v in
                (stages['degradation']['duration_growth'],
                 stages['degradation']['throughput_loss'], stages['recovery']['value'])))
        # ADAPTATION: nonfinite derived evidence is null, never a numeric decision.
        for field in ('duration_growth', 'throughput_loss'):
            value = stages['degradation'][field]
            if value is not None and not math.isfinite(value):
                stages['degradation'][field] = None
                stages['degradation'][field+'_pass'] = None
        if stages['recovery']['value'] is not None and not math.isfinite(stages['recovery']['value']):
            stages['recovery'].update(value=None, filtered=None, reason='NONFINITE_RECOVERY')
        # Preserve G01 precedence, then require strict A and the current G02 span.
        if not stages['probability']['passed'] or not stages['spacing']['passed']:
            continue
        if not arithmetic_valid:
            row.update(status='INSUFFICIENT_EVIDENCE', reason='INVALID_OR_INSUFFICIENT_ARITHMETIC')
        elif row['reason'] in ('TRANSIENT_RECOVERY', 'NO_DURATION_INCREASE'):
            continue
        elif not stages['degradation']['duration_growth_pass']:
            row.update(status='SKIPPED', reason='DURATION_GROWTH_NOT_GT_THRESHOLD')
        else:
            row['qualified_candidate'] = True
            if stages['persistence']['decision']:
                row.update(status='DETECTION_TRIGGERED', reason='APPROVED_G01_G02_G13_CONJUNCTION',
                           detection_trigger=True)
            else:
                row.update(status='QUALIFIED_CANDIDATE', reason='INCLUSIVE_SPAN_NOT_GT20')
    return rows


def _detect_approved(records, adapter, config):
    """ADAPTATION task05 opt-in; does not select C or connect a production controller."""
    evidence = dict(interface_version=APPROVED_RULES_VERSION,
        approved_packet_head=APPROVED_PACKET_HEAD,
        approved_rules=dict(G01='a', G02='inclusive_span', G13='A'),
        status='INSUFFICIENT_EVIDENCE', config=asdict(config), final_alert=False,
        detection_trigger=False, unresolved=['G20'], candidates=[], engine=None,
        input=[], latest_iteration=None)
    try:
        # G01 validation precedes serialization and numerical operations.
        validate_sequence(records)
        evidence.update(input=[asdict(r) for r in records],
                        latest_iteration=records[-1].iteration if records else None)
        prepared = preprocess(records, config)
        evidence['preprocessing'] = prepared
    except ValueError as error:
        evidence.update(status='INVALID_INPUT', reason=str(error))
        return evidence
    except (OverflowError, ArithmeticError) as error:
        evidence['reason'] = 'PREPROCESSING_ARITHMETIC_FAILED: ' + str(error)
        return evidence
    values = prepared['values_ms']
    if len(values) < 8:
        evidence['reason'] = 'NATIVE_MINIMUM_8_RETAINED_SAMPLES_GUARD'
        return evidence
    if prepared['population_std_ms'] == 0 or len(set(values)) == 1:
        evidence['reason'] = 'CONSTANT_SERIES_ZERO_VARIANCE'
        return evidence
    try:
        engine = (adapter or RbeastAdapter()).analyze(values)
        evidence['engine'] = engine
        if engine['status'] != 'OK':
            evidence.update(status=engine['status'], reason=engine.get('reason'))
            return evidence
        if engine.get('parameters') != PARAMETERS:
            raise ValueError('approved G01 parameter identity mismatch')
        # UPSTREAM raw pairing; ADAPTATION fail closed even for a replay/custom adapter.
        candidates = candidates_from_raw(engine['raw'], len(values))
        evidence['candidates'] = filter_candidates(prepared, candidates,
            records[-1].iteration, config, approved_rules=True)
    except (ValueError, TypeError, KeyError, ArithmeticError) as error:
        evidence['reason'] = 'INVALID_NATIVE_OR_ARITHMETIC: ' + str(error)
        return evidence
    evidence['detection_trigger'] = any(c['detection_trigger'] for c in evidence['candidates'])
    insufficient = any(c['status'] == 'INSUFFICIENT_EVIDENCE' for c in evidence['candidates'])
    evidence.update(status='DETECTION_TRIGGERED' if evidence['detection_trigger'] else
                    'INSUFFICIENT_EVIDENCE' if insufficient else 'NO_DETECTION_TRIGGER',
                    reason='APPROVED_DETECTION_RULES_ONLY_G20_FINAL_ALERT_UNAVAILABLE')
    return evidence


def detect(records, adapter=None, config=DetectionConfig(), *, approved_rules=False):
    if type(approved_rules) is not bool:
        raise ValueError('approved_rules must be an explicit bool')
    if approved_rules:
        return _detect_approved(records, adapter, config)
    evidence=dict(status='AMBIGUOUS_SPEC',config=asdict(config),final_alert=False,
                  unresolved=['G01','G02','G13','G20'],candidates=[],engine=None,
                  input=[asdict(r) for r in records],latest_iteration=records[-1].iteration if records else None)
    try:
        prepared=preprocess(records,config);evidence['preprocessing']=prepared
    except ValueError as error:
        evidence.update(status='INVALID_INPUT',reason=str(error));return evidence
    values=prepared['values_ms']
    if len(values)<8:
        evidence.update(status='INSUFFICIENT_EVIDENCE',reason='NATIVE_MINIMUM_8_RETAINED_SAMPLES_GUARD');return evidence
    if prepared['population_std_ms']==0 or len(set(values))==1:
        evidence.update(status='INSUFFICIENT_EVIDENCE',reason='CONSTANT_SERIES_ZERO_VARIANCE');return evidence
    engine=(adapter or RbeastAdapter()).analyze(values);evidence['engine']=engine
    if engine['status']!='OK':
        evidence.update(status=engine['status'],reason=engine.get('reason'));return evidence
    evidence['candidates']=filter_candidates(prepared,engine['candidates'],records[-1].iteration,config)
    evidence['reason']='STATISTICAL_EVIDENCE_ONLY_NO_APPROVED_FINAL_ALERT'
    return evidence


def prefix_replay(records, adapter=None, *, approved_rules=False):
    """Publication order, never sort or use records from k+1 in decision k."""
    return [detect(records[:k],adapter,approved_rules=approved_rules)
            for k in range(1,len(records)+1)] or [detect([],adapter,approved_rules=approved_rules)]
