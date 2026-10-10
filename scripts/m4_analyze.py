"""ADAPTATION: independent offline CLI, no evaluator truth arguments."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flash.localization import analyze
from flash.profile_input import read_records


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True, help="schema1 bundle; or manifest for source ingestion")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--format", choices=["normalized", "m3_ndjson", "m3_csv"], default="normalized")
    p.add_argument("--records", type=Path, nargs="+")
    p.add_argument("--supplements", type=Path)
    a = p.parse_args()
    try:
        bundle = json.loads(a.input.read_text())
        if a.format != "normalized":
            if not a.records:
                raise ValueError("source format needs --records")
            extras = json.loads(a.supplements.read_text()) if a.supplements else None
            bundle["records"], audit = read_records(a.records, a.format, bundle["context"], extras)
        else:
            audit = []
        result = analyze(bundle)
        result["source_audit"] = audit
        code = 0
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as error:
        result = dict(status="REJECTED_INPUT", candidate_ranks=[], final_fault_ranks=[], reason=str(error),
            completeness=dict(verified=False, policy="fail closed; no invalid/missing duration enters statistics"))
        code = 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+"\n")
    print(json.dumps(dict(status=result["status"], candidate_ranks=result["candidate_ranks"], exit_code=code)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
