"""PAPER: two-stage max-group/min-rank ordering; unresolved G04 stays provisional."""
import math
import statistics
from collections import defaultdict
from flash.profile_input import validate_bundle

CV_THRESHOLD = 0.1  # PAPER §3.3.2 p34


def mean(values):
    # ADAPTATION: scale before summing to avoid overflow of finite input durations.
    scale = max(values)
    return scale * (math.fsum(v / scale for v in values) / len(values)) if scale else 0.0


def cv(values):
    mu = mean(values)
    if mu == 0:
        return dict(mean_us=0.0, population=None, sample=None, decision="AMBIGUOUS_SPEC", reason="ZERO_MEAN_CV_UNDEFINED")
    ratios = [v / mu for v in values]
    pop = statistics.pstdev(ratios)
    sample = statistics.stdev(ratios) if len(values) > 1 else None
    decision = "BELOW" if pop < CV_THRESHOLD else "ABOVE"
    if sample is not None and (pop < CV_THRESHOLD) != (sample < CV_THRESHOLD):
        decision = "AMBIGUOUS_SPEC"
    return dict(mean_us=mu, population=pop, sample=sample, decision=decision,
        convention="population baseline; sample sensitivity (ADAPTATION G04)")


def clique_scores(clique_means):
    """PAPER Eq3-1: group MEAN versus unweighted same-tag group means; never max."""
    mu = mean(list(clique_means.values()))
    return dict(reference_mean_us=mu, status="DEFINED" if mu else "ZERO_REFERENCE",
        scores={key: (value/mu-1) if mu else None for key,value in clique_means.items()})


def rank_scores(rank_means):
    """PAPER Eq3-2; ranking statistics, not a calibrated probability."""
    mu = mean(list(rank_means.values()))
    return dict(reference_mean_us=mu, status="DEFINED" if mu else "ZERO_REFERENCE",
        scores={str(key): (1-value/mu) if mu else None for key,value in rank_means.items()})


def extrema(values, highest=False):
    target = (max if highest else min)(values.values())
    return sorted(key for key,value in values.items() if value == target)


def rank_analysis(group):
    outputs = {}
    for method in ("unweighted_communicator_mean", "sample_weighted"):
        stats = group["rank_statistics"][method]
        test = cv(list(stats.values()))
        candidates = extrema(stats) if test["decision"] == "ABOVE" else []
        outputs[method] = dict(avg_latency_us={str(k):v for k,v in stats.items()}, cv=test,
            candidates=candidates, rank_scores=rank_scores(stats), rule="minimum avg_latency; 20% filter unresolved and disabled")
    left, right = outputs.values()
    ambiguous = any(v["cv"]["decision"] == "AMBIGUOUS_SPEC" for v in outputs.values()) or left["candidates"] != right["candidates"]
    if ambiguous:
        status = "AMBIGUOUS_SPEC"
    elif left["candidates"]:
        status = "PROVISIONAL_CANDIDATE"
    else:
        status = "NO_CANDIDATE"
    return dict(status=status, sensitivity_disagreement=left["candidates"] != right["candidates"], methods=outputs)


def analyze(bundle):
    valid = validate_bundle(bundle)
    groups = {}
    for h, declaration in valid["declarations"].items():
        locals_, rank_values, rank_local_means = [], defaultdict(list), defaultdict(list)
        for key, timing_values in valid["instances"].items():
            if key[0] != h:
                continue
            values = list(timing_values.values())
            mu = mean(values)
            locals_.append(dict(node_id=key[1], global_rank=key[2], process_instance=key[3], comm_generation=key[4],
                avg_latency_us=mu, sample_count=len(values), min_us=min(values), max_us=max(values)))
            rank_values[key[2]].extend(values)
            rank_local_means[key[2]].append(mu)
        rank_stats = dict(unweighted_communicator_mean={r:mean(v) for r,v in rank_local_means.items()}, sample_weighted={r:mean(v) for r,v in rank_values.items()})
        groups[h] = dict(id_hash=h, members=sorted(declaration["members"]), local_communicators=locals_,
            max_avg_latency_us=max(c["avg_latency_us"] for c in locals_),
            clique_mean_us=mean([c["avg_latency_us"] for c in locals_]), rank_statistics=rank_stats)
    tags, evidence, ambiguity = {}, defaultdict(list), False
    for label, identities in sorted(valid["tags"].items()):
        usable = [h for h in identities if len(groups[h]["members"]) > 1]
        row = dict(excluded_single_rank=[h for h in identities if h not in usable], selected_groups=[], stage2={})
        if not usable:
            row.update(status="NO_CANDIDATE", reason="NO_MULTIRANK_GROUP")
        else:
            scores = {h:groups[h]["max_avg_latency_us"] for h in usable}
            row["max_avg_latency_us"] = scores
            row["clique_scores"] = clique_scores({h:groups[h]["clique_mean_us"] for h in usable})
            if len(usable) == 1:
                chosen = usable
                row.update(stage1="SINGLE_GROUP_DIRECT", group_cv=None)
            else:
                test = cv(list(scores.values()))
                row["group_cv"] = test
                chosen = extrema(scores, highest=True) if test["decision"] == "ABOVE" else []
                row["stage1"] = "MAX_GROUP" if chosen else "CV_SKIP" if test["decision"] == "BELOW" else "AMBIGUOUS_SPEC"
            row["selected_groups"] = chosen
            if not chosen:
                row["status"] = "AMBIGUOUS_SPEC" if row["stage1"] == "AMBIGUOUS_SPEC" else "NO_CANDIDATE"
            else:
                row["stage2"] = {h:rank_analysis(groups[h]) for h in chosen}
                statuses = {v["status"] for v in row["stage2"].values()}
                row["status"] = "AMBIGUOUS_SPEC" if "AMBIGUOUS_SPEC" in statuses else "PROVISIONAL_CANDIDATE" if "PROVISIONAL_CANDIDATE" in statuses else "NO_CANDIDATE"
                for h, result in row["stage2"].items():
                    for method, stats in result["methods"].items():
                        for rank in stats["candidates"]:
                            evidence[rank].append(dict(label=label, id_hash=h, method=method, status=result["status"],
                                avg_latency_us=stats["avg_latency_us"][str(rank)], rank_cv=stats["cv"],
                                comparison_rank_means_us=stats["avg_latency_us"], rule="min rank after max group/CV"))
        ambiguity |= row["status"] == "AMBIGUOUS_SPEC"
        tags[label] = row
    conflict = len(evidence) > 1
    if ambiguity or conflict:
        status = "AMBIGUOUS_SPEC"
    elif evidence:
        status = "PROVISIONAL_CANDIDATE"
    else:
        status = "NO_CANDIDATE"
    public_groups = {}
    for h, g in groups.items():
        public_groups[h] = {k:v for k,v in g.items() if k != "rank_statistics"}
    return dict(schema_version=1, context=valid["context"], status=status, final_fault_ranks=[],
        candidate_ranks=sorted(evidence), tags=tags, groups=public_groups,
        cross_tag=dict(conflict=conflict, support={str(rank):dict(labels=sorted({e["label"] for e in rows}), evidence=rows) for rank,rows in evidence.items()}),
        completeness=valid["completeness"], measurement_signatures=valid["measurement_signatures"], risks=valid["risks"],
        unresolved=["G04: 20% reference/filter undefined", "G04: communicator aggregation weights undefined", "G04: statistical references and std convention not uniquely specified"],
        interpretation="Offline ordering evidence only; no final fault decision, probability or automatic diagnosis")
