"""PAPER: two-stage max-group/min-rank ordering; unresolved G04 stays provisional."""
import math
import statistics
from collections import defaultdict
from fractions import Fraction
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


# ADAPTATION: explicit task07 entry; analyze() above retains the original M4 contract.
G04_RULES = ("S1-MAX", "W-EQUAL", "R-GROUP", "T-GE", "C-GUARD",
             "N-GUARD", "Q-TWO", "F-PROVISIONAL")


def _g04_cv(values):
    """ADAPTATION C/N-GUARD: exact gates audit the saved binary64 input means."""
    test = cv(values)
    test["input_means_hex"] = [float(x).hex() for x in values]
    exact = [Fraction(x) for x in values]
    mu = sum(exact) / len(exact)
    test["reasons"] = []
    if not mu:
        test["reasons"].append("ZERO_MEAN_CV_UNDEFINED")
        return test
    if len(values) < 2:
        test.update(decision="AMBIGUOUS_SPEC")
        test["reasons"].append("CV_SAMPLE_UNDEFINED")
        return test
    ss = sum((x - mu) ** 2 for x in exact)
    squared = {"population": ss / len(exact) / mu ** 2,
               "sample": ss / (len(exact) - 1) / mu ** 2}
    test["exact_squared_cv"] = {k: str(v) for k, v in squared.items()}
    rational = {k: v >= Fraction(1, 100) for k, v in squared.items()}
    floating = {k: test[k] >= CV_THRESHOLD for k in squared}
    test["exact_gate"] = rational
    test["floating_gate"] = floating
    if floating["population"] != floating["sample"]:
        test["reasons"].append("CV_CONVENTION_DISAGREEMENT")
    if floating != rational:
        test["reasons"].append("CV_NUMERIC_DISAGREEMENT")
    if test["reasons"]:
        test["decision"] = "AMBIGUOUS_SPEC"
    return test


def _g04_threshold(rank_means, rank):
    """ADAPTATION R-GROUP/T-GE/N-GUARD; PAPER Eq3-2 reference and direction."""
    mu = mean(list(rank_means.values()))
    exact_mu = sum(Fraction(x) for x in rank_means.values()) / len(rank_means)
    if not mu or not exact_mu:
        return dict(decision="AMBIGUOUS_SPEC", reason="ZERO_OUTLIER_DENOMINATOR",
                    score=None, reference_mean_us=mu)
    # Literal approved (group mean - rank mean) / group mean. Nonnegative
    # timings make this subtraction safe from overflow. No epsilon or rounding.
    score = (mu - rank_means[rank]) / mu
    exact_score = (exact_mu - Fraction(rank_means[rank])) / exact_mu
    floating, rational = score >= 0.2, exact_score >= Fraction(1, 5)
    return dict(decision="AMBIGUOUS_SPEC" if floating != rational else "PASS" if floating else "REJECT",
                reason="RANK_NUMERIC_DISAGREEMENT" if floating != rational else None,
                score=score, score_hex=score.hex(), reference_mean_us=mu,
                exact_score=str(exact_score), exact_reference_mean_us=str(exact_mu),
                floating_gate=floating, exact_gate=rational)


def _g04_groups(valid):
    """Same M4 aggregation, with per-instance deduplicated scope provenance."""
    groups = {}
    for h, declaration in valid["declarations"].items():
        locals_, by_rank, rank_local_means = [], defaultdict(list), defaultdict(list)
        for key, scopes in valid["instances"].items():
            if key[0] != h:
                continue
            values = list(scopes.values())
            mu = mean(values)
            locals_.append(dict(node_id=key[1], global_rank=key[2], process_instance=key[3],
                comm_generation=key[4], avg_latency_us=mu, sample_count=len(values),
                min_us=min(values), max_us=max(values), timing_scopes=[list(s) for s in scopes]))
            by_rank[key[2]].extend(values)
            rank_local_means[key[2]].append(mu)
        groups[h] = dict(id_hash=h, members=sorted(declaration["members"]), local_communicators=locals_,
            max_avg_latency_us=max(c["avg_latency_us"] for c in locals_),
            clique_mean_us=mean([c["avg_latency_us"] for c in locals_]),
            rank_statistics=dict(unweighted_communicator_mean={r: mean(v) for r, v in rank_local_means.items()},
                                 sample_weighted={r: mean(v) for r, v in by_rank.items()}))
    return groups


def _g04_rank_analysis(group):
    means = group["rank_statistics"]["unweighted_communicator_mean"]
    scope_means = group["rank_statistics"]["sample_weighted"]
    minima = extrema(means)
    test = _g04_cv(list(means.values()))
    insufficient = [c for c in group["local_communicators"] if c["sample_count"] < 2]
    # Observations survive Q-TWO; they never become manufactured time samples.
    row = dict(avg_latency_us={str(r): v for r, v in means.items()}, cv=test,
               minimum_ranks=minima, candidates=[], thresholds={}, reasons=[],
               insufficient_instances=insufficient,
               sensitivity=dict(W_SCOPE=dict(diagnostic_only=True,
                   avg_latency_us={str(r): v for r, v in scope_means.items()},
                   minimum_ranks=extrema(scope_means), cv=_g04_cv(list(scope_means.values())))))
    if insufficient:
        row.update(status="INCOMPLETE", reasons=["SINGLE_SCOPE_INSTANCE"])
        return row
    if test["decision"] == "AMBIGUOUS_SPEC":
        row.update(status="AMBIGUOUS_SPEC", reasons=test["reasons"])
        return row
    if test["decision"] == "BELOW":
        row.update(status="NO_CANDIDATE")
        return row
    if len(minima) > 1:
        row["reasons"].append("MIN_RANK_TIE")
    for rank in minima:
        threshold = _g04_threshold(means, rank)
        row["thresholds"][str(rank)] = threshold
        if threshold["decision"] == "AMBIGUOUS_SPEC":
            row["reasons"].append(threshold["reason"])
        elif threshold["decision"] == "PASS":
            row["candidates"].append(rank)
    row["status"] = ("AMBIGUOUS_SPEC" if row["reasons"] else
                     "PROVISIONAL_CANDIDATE" if row["candidates"] else "NO_CANDIDATE")
    return row


def analyze_approved_g04(bundle):
    """Task07 CPU opt-in only. No controller integration or final fault alerts.

    PAPER: Stage1 maximum communicator mean, Stage2 minimum rank, plot mean
    separate (§3.2.3/3.3.2; Eq3-1/3-2). ADAPTATION: eight owner-approved rules
    recorded in docs/m6b-ready/g3-g04-implementation/APPROVAL.json.
    """
    result = dict(schema_version=1, ruleset="G04-task07-v1", rules=list(G04_RULES),
                  final_fault_ranks=[], final_alert=False, candidate_ranks=[],
                  tags={}, groups={}, reasons=[], cross_tag=dict(conflict=False, support={}))
    try:
        valid = validate_bundle(bundle)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        result.update(status="INCOMPLETE", reasons=["INVALID_OR_MISSING_PROFILE_EVIDENCE"],
                      input_error=str(error), completeness=dict(verified=False))
        return result
    groups = _g04_groups(valid)
    evidence = defaultdict(list)
    statuses = []
    for label, identities in sorted(valid["tags"].items()):
        usable = sorted(h for h in identities if len(groups[h]["members"]) > 1)
        row = dict(excluded_single_rank=sorted(h for h in identities if h not in usable),
                   selected_groups=[], stage2={}, reasons=[], status="NO_CANDIDATE")
        if not usable:
            row["stage1"] = "NO_MULTIRANK_GROUP"
        else:
            maxima = {h: groups[h]["max_avg_latency_us"] for h in usable}
            row["max_avg_latency_us"] = maxima
            row["clique_scores"] = clique_scores({h: groups[h]["clique_mean_us"] for h in usable})
            if len(usable) == 1:
                row.update(stage1="SINGLE_GROUP_DIRECT", group_cv=None, selected_groups=usable)
            else:
                test = _g04_cv(list(maxima.values()))
                row["group_cv"] = test
                row["stage1"] = "MAX_GROUP" if test["decision"] == "ABOVE" else "CV_SKIP"
                if test["decision"] == "AMBIGUOUS_SPEC":
                    row.update(stage1="AMBIGUOUS_SPEC", status="AMBIGUOUS_SPEC", reasons=test["reasons"])
                elif test["decision"] == "ABOVE":
                    row["selected_groups"] = extrema(maxima, highest=True)
            if len(row["selected_groups"]) > 1:
                row["reasons"].append("MAX_GROUP_TIE")
            for h in row["selected_groups"]:
                analysis = _g04_rank_analysis(groups[h])
                row["stage2"][h] = analysis
                row["reasons"].extend(analysis["reasons"])
                for rank in analysis["candidates"]:
                    evidence[rank].append(dict(label=label, id_hash=h, rank=rank,
                        method="W-EQUAL", status=analysis["status"],
                        avg_latency_us=analysis["avg_latency_us"][str(rank)],
                        threshold=analysis["thresholds"][str(rank)],
                        comparison_rank_means_us=analysis["avg_latency_us"],
                        local_communicators=[c for c in groups[h]["local_communicators"] if c["global_rank"] == rank]))
            child_statuses = {v["status"] for v in row["stage2"].values()}
            if "INCOMPLETE" in child_statuses:
                row["status"] = "INCOMPLETE"
            elif row["reasons"]:
                row["status"] = "AMBIGUOUS_SPEC"
            elif "PROVISIONAL_CANDIDATE" in child_statuses:
                row["status"] = "PROVISIONAL_CANDIDATE"
        row["reasons"] = sorted(set(row["reasons"]))
        result["tags"][label] = row
        result["reasons"].extend(row["reasons"])
        statuses.append(row["status"])
    conflict = len(evidence) > 1
    if conflict:
        result["reasons"].append("DIFFERENT_RANK_CONFLICT")
    status = ("INCOMPLETE" if "INCOMPLETE" in statuses else
              "AMBIGUOUS_SPEC" if "AMBIGUOUS_SPEC" in statuses or conflict else
              "PROVISIONAL_CANDIDATE" if evidence else "NO_CANDIDATE")
    result.update(status=status, context=valid["context"], candidate_ranks=sorted(evidence),
        groups={h: {k: v for k, v in g.items() if k != "rank_statistics"} for h, g in groups.items()},
        cross_tag=dict(conflict=conflict, support={str(r): dict(labels=sorted({e["label"] for e in rows}), evidence=rows)
                                               for r, rows in evidence.items()}),
        completeness=valid["completeness"], measurement_signatures=valid["measurement_signatures"],
        risks=valid["risks"], reasons=sorted(set(result["reasons"])),
        interpretation="Provisional timing evidence; declared labels only, no fault probability or final diagnosis")
    return result
