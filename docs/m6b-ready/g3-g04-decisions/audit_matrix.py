"""ADAPTATION: read-only G04 decision analysis; never imported by FLASH.

PAPER sources and proposed formula IDs are in G04_DECISION_PACKET.md.
EXTENSION: Cartesian sensitivity, including hypothetical final eligibility.
No expected label, evaluator target or scenario enters decide().
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import platform
import runpy
import statistics
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def avg(v):
    scale = max(v)
    return scale * (math.fsum(x / scale for x in v) / len(v)) if scale else 0.0


def cvs(v):
    mu = avg(v)
    if not mu:
        return {"population": None, "sample": None, "mean_us": mu}
    ratios = [x / mu for x in v]
    exact_values = [Fraction(x) for x in v]
    exact_mean = sum(exact_values) / len(v)
    sum_squares = sum((x - exact_mean) ** 2 for x in exact_values)
    exact_population_pass = sum_squares / len(v) / exact_mean ** 2 >= Fraction(1, 100)
    exact_sample_pass = sum_squares / (len(v) - 1) / exact_mean ** 2 >= Fraction(1, 100) if len(v) > 1 else None
    return {"population": statistics.pstdev(ratios),
            "sample": statistics.stdev(ratios) if len(v) > 1 else None,
            "mean_us": mu, "exact_squared_CV_gate": {"population": exact_population_pass, "sample": exact_sample_pass}}


def gate(v, mode):
    c = cvs(v)
    if c["population"] is None or c["sample"] is None:
        return "AMBIGUOUS_SPEC"
    p, s = c["population"] >= .1, c["sample"] >= .1
    exact = c["exact_squared_CV_gate"]
    if (mode in ("guard", "population") and p != exact["population"]) or (mode in ("guard", "sample") and s != exact["sample"]):
        return "AMBIGUOUS_SPEC"
    if mode == "guard" and p != s:
        return "AMBIGUOUS_SPEC"
    return "ABOVE" if (s if mode == "sample" else p) else "BELOW"


def rank_parts(means, rank, reference):
    """Only the minimum rank is tested; no multiple-outlier scan."""
    x = means[rank]
    others = [v for r, v in means.items() if r != rank]
    if reference == "group_mean":
        ref = avg(list(means.values()))
        den = ref
    elif reference == "peer_mean":
        ref = avg(others)
        den = ref
    elif reference == "peer_over_min":
        ref = avg(others)
        den = x
    elif reference == "nearest_peer":
        ref = min(others)
        den = ref
    else:
        raise ValueError(reference)
    return ref, x, den


def rank_score(means, rank, reference):
    ref, x, den = rank_parts(means, rank, reference)
    return None if den == 0 else (ref / den - x / den)


def threshold_decision(means, rank, reference, comparator):
    ref, x, den = rank_parts(means, rank, reference)
    score = rank_score(means, rank, reference)
    if score is None:
        return "AMBIGUOUS_SPEC"
    floating = score >= .2 if comparator == "ge" else score > .2
    # No tolerance band. Exact rational arithmetic on the already computed
    # binary64 means audits cancellation; it does not claim exact physical times.
    exact_x = Fraction(means[rank])
    exact_others = [Fraction(v) for r, v in means.items() if r != rank]
    if reference == "group_mean":
        exact_ref = sum(Fraction(v) for v in means.values()) / len(means)
        exact_den = exact_ref
    elif reference in ("peer_mean", "peer_over_min"):
        exact_ref = sum(exact_others) / len(exact_others)
        exact_den = exact_x if reference == "peer_over_min" else exact_ref
    else:
        exact_ref = min(exact_others)
        exact_den = exact_ref
    exact = (exact_ref - exact_x) / exact_den
    rational = exact >= Fraction(1, 5) if comparator == "ge" else exact > Fraction(1, 5)
    if floating != rational:
        return "AMBIGUOUS_SPEC"
    return "PASS" if floating else "REJECT"


def from_valid(valid):
    groups = {}
    for h, declaration in valid["declarations"].items():
        instances = []
        for key, scopes in valid["instances"].items():
            if key[0] == h:
                values = list(scopes.values())
                instances.append({"rank": key[2], "mean_us": avg(values),
                                  "samples": len(values), "values_us": values})
        groups[h] = {"members": sorted(declaration["members"]), "instances": instances}
    return {"groups": groups, "tags": valid["tags"], "risks": valid["risks"]}


def group_statistics(group, weight):
    by_rank = defaultdict(list)
    for local in group["instances"]:
        by_rank[local["rank"]].append(local)
    means = {}
    for rank, local in by_rank.items():
        if weight == "equal":
            means[rank] = avg([i["mean_us"] for i in local])
        else:
            means[rank] = avg([x for i in local for x in i["values_us"]])
    return means


def decide(data, policy):
    weight, convention, reference, comparator, samples, conflict_rule = policy
    support = defaultdict(set)
    ambiguity = False
    incomplete = False
    tie = False
    reasons = []
    tag_rows = {}
    for label, identities in sorted(data["tags"].items()):
        usable = [h for h in identities if len(data["groups"][h]["members"]) > 1]
        selected = []
        if len(usable) == 1:
            selected = usable
        elif len(usable) > 1:
            maxima = {h: max(i["mean_us"] for i in data["groups"][h]["instances"]) for h in usable}
            g = gate(list(maxima.values()), convention)
            if g == "AMBIGUOUS_SPEC":
                ambiguity = True
                reasons.append("STAGE1_CV_UNDEFINED_OR_CONVENTION")
            if g == "ABOVE":
                selected = [h for h in usable if maxima[h] == max(maxima.values())]
        if len(selected) > 1:
            tie = True
            reasons.append("MAX_GROUP_TIE")
        tag_ranks = set()
        for h in selected:
            group = data["groups"][h]
            if samples == "require2" and any(i["samples"] < 2 for i in group["instances"]):
                incomplete = True
                reasons.append("SINGLE_SCOPE_INSTANCE")
                continue
            means = group_statistics(group, weight)
            g = gate(list(means.values()), convention)
            if g == "AMBIGUOUS_SPEC":
                ambiguity = True
                reasons.append("STAGE2_CV_UNDEFINED_OR_CONVENTION")
            if g != "ABOVE":
                continue
            minima = [r for r, value in means.items() if value == min(means.values())]
            if len(minima) > 1:
                tie = True
                reasons.append("MIN_RANK_TIE")
            for rank in minima:
                score = rank_score(means, rank, reference)
                threshold = threshold_decision(means, rank, reference, comparator)
                if threshold == "AMBIGUOUS_SPEC":
                    ambiguity = True
                    reasons.append("ZERO_OUTLIER_DENOMINATOR" if score is None else "FLOAT_THRESHOLD_DISAGREEMENT")
                elif threshold == "PASS":
                    support[rank].add(label)
                    tag_ranks.add(rank)
        tag_rows[label] = {"selected_groups": selected, "candidate_ranks": sorted(tag_ranks)}
    ranks = sorted(support)
    if incomplete:
        status = "INCOMPLETE"
    elif ambiguity or tie or len(ranks) > 1:
        status = "AMBIGUOUS_SPEC"
    elif not ranks:
        status = "NO_CANDIDATE"
    else:
        status = "PROVISIONAL_CANDIDATE"
    final_eligible = []
    if status == "PROVISIONAL_CANDIDATE":
        if conflict_rule == "single_final" or (conflict_rule == "two_label_final" and len(support[ranks[0]]) >= 2):
            final_eligible = ranks
    return {"status": status, "candidate_ranks": ranks, "hypothetical_final_eligible": final_eligible,
            "support_labels": {str(r): sorted(support[r]) for r in ranks},
            "tags": tag_rows, "reasons": sorted(set(reasons)), "live_final_fault_ranks": []}


def diagnostics(data):
    result = {}
    for h, group in data["groups"].items():
        methods = {}
        for weight in ["equal", "scope"]:
            means = group_statistics(group, weight)
            minima = [r for r, v in means.items() if v == min(means.values())]
            scores = {str(r): {ref: rank_score(means, r, ref) for ref in
                      ["group_mean", "peer_mean", "peer_over_min", "nearest_peer"]}
                      for r in minima if len(means) > 1}
            methods[weight] = {"rank_means_us": means, "cv": cvs(list(means.values())),
                               "minimum_ranks": minima, "scores": scores}
        result[h] = {"members": group["members"], "local_scope_counts": [i["samples"] for i in group["instances"]],
                     "max_avg_latency_us": max(i["mean_us"] for i in group["instances"]),
                     "clique_mean_us": avg([i["mean_us"] for i in group["instances"]]), "methods": methods}
    result["label_stage1"] = {}
    for label, hashes in data["tags"].items():
        usable = [h for h in hashes if len(data["groups"][h]["members"]) > 1]
        maxima = {h: result[h]["max_avg_latency_us"] for h in usable}
        clique_mean_reference = avg([result[h]["clique_mean_us"] for h in usable]) if usable else None
        result["label_stage1"][label] = {"maxima_us": maxima,
            "cv": cvs(list(maxima.values())) if len(maxima) > 1 else None,
            "plot_clique_reference_us": clique_mean_reference,
            "plot_clique_scores": {h: result[h]["clique_mean_us"] / clique_mean_reference - 1 if clique_mean_reference else None for h in usable}}
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    source = args.source.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(source))
    from flash.profile_input import validate_bundle, read_records, InputError
    from flash.localization import analyze
    verify = runpy.run_path(str(source / "tests/m4_offline.py"))["verify"]
    inputs = {}
    rows = []
    fixture_checks = []
    def read(path):
        inputs[str(path.relative_to(source))] = digest(path)
        return json.loads(path.read_text())
    names = read(source / "tests/m4_cases/index.json")
    assert len(names) == 65
    for name in names:
        folder = source / "tests/m4_cases" / name
        bundle = read(folder / "input.json")
        expected = read(folder / "expected.json")
        saved = read(source / "docs/m4/fixtures" / name / "actual.json")
        exit_path = source / "docs/m4/fixtures" / name / "exit_code.txt"
        inputs[str(exit_path.relative_to(source))] = digest(exit_path)
        assert int(exit_path.read_text()) == expected["exit_code"]
        verify(saved, expected["checks"])
        try:
            if (folder / "ingestion.json").exists():
                config = read(folder / "ingestion.json")
                supplements = read(folder / config["supplements"]) if config.get("supplements") else None
                paths = [folder / path for path in config["records"]]
                for path in paths:
                    inputs[str(path.relative_to(source))] = digest(path)
                bundle["records"], _ = read_records(paths, config["format"], bundle["context"], supplements)
            valid = validate_bundle(bundle)
            actual = analyze(bundle)
            verify(actual, expected["checks"])
            assert expected["exit_code"] == 0
            assert actual["candidate_ranks"] == saved["candidate_ranks"] and actual["status"] == saved["status"]
            rows.append({"id": "fixture/" + name, "kind": "synthetic_fixture", "data": from_valid(valid),
                         "baseline": {"status": actual["status"], "candidate_ranks": actual["candidate_ranks"]}})
            fixture_checks.append({"name": name, "status": "PASS", "expected_exit": 0})
        except (InputError, KeyError, ValueError, TypeError) as error:
            assert expected["exit_code"] == 2, (name, str(error))
            rows.append({"id": "fixture/" + name, "kind": "invalid_fixture", "data": None,
                         "reason": str(error), "baseline": {"status": saved["status"], "candidate_ranks": []}})
            fixture_checks.append({"name": name, "status": "PASS", "expected_exit": 2, "reason": str(error)})
    supplement = read(source / "docs/m4/supplement/samples.json")
    results = read(source / "docs/m4/supplement/results.json")["results"]
    lookup = {(r["run_id"], r["epoch"]): r for r in results}
    assert len(supplement["bundles"]) == len(results) == 30
    for bundle in supplement["bundles"]:
        valid = validate_bundle(bundle)
        baseline = analyze(bundle)
        key = (bundle["context"]["run_id"], bundle["context"]["profile_epoch"])
        historical = lookup[key]
        assert baseline == historical["prediction"]
        rows.append({"id": key[0] + "/epoch" + str(key[1]), "kind": "m4_supplement",
                     "data": from_valid(valid), "baseline": {"status": baseline["status"], "candidate_ranks": baseline["candidate_ranks"]},
                     "evaluation_only": historical["evaluator"], "layout": historical["layout"]})
    for epoch in [1, 2]:
        bundle = read(source / ("docs/m4/multigroup-input-epoch%d.json" % epoch))
        valid = validate_bundle(bundle)
        baseline = analyze(bundle)
        saved = read(source / ("docs/m4/multigroup-prediction-epoch%d.json" % epoch))
        assert baseline == saved
        rows.append({"id": "m4-multigroup-normal-01/epoch" + str(epoch), "kind": "m4_original_normal",
                     "data": from_valid(valid), "baseline": {"status": baseline["status"], "candidate_ranks": baseline["candidate_ranks"]},
                     "evaluation_only": {"truth_ranks": [], "scenario": "normal"}})
    # Public M3 samples: predetermined historical selection only; no forged raw schema/identity.
    samples = []
    for node in [0, 1]:
        path = source / ("docs/m3/samples-node-%d.csv" % node)
        inputs[str(path.relative_to(source))] = digest(path)
        with path.open() as stream:
            samples.extend(csv.DictReader(stream))
    history = read(source / "docs/m4/m3-replay.json")["results"]
    hist = {(r["run_id"], r["epoch"], r.get("window_id"), r.get("selection_policy")): r for r in history if "window_id" in r}
    for run, epoch in itertools.product(["m3abc-local-01", "m3d-roce-01"], [1, 2]):
        for index, case in enumerate(["normal", "cpu0", "cpu1", "gpu0", "gpu1"], 1):
            for policy in ["all13", "fixed_warmup3"]:
                selected = [r for r in samples if r["run_id"] == run and int(r["profile_epoch"]) == epoch and
                            r["case"] == case and (policy == "all13" or r["warmup"] == "False")]
                instances = []
                for rank in [0, 1]:
                    rr = [r for r in selected if int(r["rank"]) == rank]
                    assert len(rr) == (13 if policy == "all13" else 10)
                    vv = [float(r["duration_us"]) for r in rr]
                    assert all(math.isfinite(v) and v > 0 for v in vv)
                    instances.append({"rank": rank, "mean_us": avg(vv), "samples": len(vv), "values_us": vv})
                hashes = {r["comm_id_hash"] for r in selected}
                assert len(hashes) == 1
                h = next(iter(hashes))
                old = hist[(run, epoch, "w" + str(index), policy)]
                data = {"groups": {h: {"members": [0, 1], "instances": instances}}, "tags": {"mechanism_pair": [h]}, "risks": []}
                no_filter = gate([i["mean_us"] for i in instances], "guard")
                candidate = [i["rank"] for i in instances if i["mean_us"] == min(j["mean_us"] for j in instances)] if no_filter == "ABOVE" else []
                assert candidate == old["candidate_ranks"]
                rows.append({"id": "%s/epoch%d/w%d/%s" % (run, epoch, index, policy), "kind": "m3_public_sufficient_statistics",
                             "data": data, "baseline": {"status": old["status"], "candidate_ranks": old["candidate_ranks"]},
                             "evaluation_only": {"truth_ranks": old["truth_ranks"], "scenario": old["case"]},
                             "validation_level": "public_samples; historical M4 raw validation inherited, not remeasured"})
    policies = list(itertools.product(["equal", "scope"], ["population", "sample", "guard"],
                    ["group_mean", "peer_mean", "peer_over_min", "nearest_peer"], ["gt", "ge"],
                    ["observational", "require2"], ["conservative", "single_final", "two_label_final"]))
    recommended = ("equal", "guard", "group_mean", "ge", "require2", "conservative")
    evaluations = []
    for row in rows:
        matrix = []
        for policy in policies:
            result = decide(row["data"], policy) if row["data"] else {"status": "INCOMPLETE", "candidate_ranks": [], "hypothetical_final_eligible": []}
            matrix.append([result["status"], result["candidate_ranks"], result["hypothetical_final_eligible"]])
        rec = decide(row["data"], recommended) if row["data"] else {"status": "INCOMPLETE", "candidate_ranks": [], "live_final_fault_ranks": []}
        # Truth is joined after every decision has already completed.
        if "evaluation_only" in row:
            evaluations.append({"id": row["id"], "kind": row["kind"], "layout": row.get("layout"),
                                "truth_ranks": row["evaluation_only"]["truth_ranks"], "baseline": row["baseline"], "recommended": rec})
        row["diagnostics"] = diagnostics(row["data"]) if row["data"] else None
        row["recommended"] = rec
        row["matrix"] = matrix
        row.pop("data")
    summary = {"rows": len(rows), "policies": len(policies), "cells": len(rows) * len(policies),
               "fixture_checks": len(fixture_checks), "kinds": dict(Counter(r["kind"] for r in rows)),
               "recommended_statuses": dict(Counter(r["recommended"]["status"] for r in rows)), "approval": None,
               "final_alert": False, "new_native_fits": 0, "new_GPU_runs": 0}
    boundaries = []
    for values in ([79, 121], [80, 120], [81, 119], [90, 110], [92, 108], [0, 0], [0, 20], [20, 20]):
        means = dict(enumerate(values))
        boundaries.append({"values_us": values, "CV": cvs(values),
            "comparisons": {ref: {op: threshold_decision(means, 0, ref, op) for op in ["gt", "ge"]}
                            for ref in ["group_mean", "peer_mean", "peer_over_min", "nearest_peer"]},
            "score": {ref: rank_score(means, 0, ref) for ref in ["group_mean", "peer_mean", "peer_over_min", "nearest_peer"]}})
    output = {"summary": summary, "arithmetic_boundaries": boundaries, "policy_fields": ["communicator_weight", "CV", "20pct_reference", "20pct_comparator", "minimum_scope_support", "conflict_final_policy"],
              "policies": policies, "recommended_policy": recommended, "fixtures": fixture_checks, "rows": rows,
              "evaluation_only": evaluations, "input_sha256": inputs, "source_head_required": "7588873d705668497694ac1d12041db5005e4b49",
              "host": platform.node(), "platform": platform.platform(), "python": sys.version, "argv": sys.argv,
              "auditor_sha256": digest(Path(__file__))}
    (args.output / "matrix.json").write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
