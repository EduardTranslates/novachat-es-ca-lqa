"""
calibrate_judge.py - Measure the refund judge and the regex checks against human labels.

Reads judge_calibration.jsonl (20 answers to EC-005/EC-006, each labelled PASS or FAIL
by a human reviewer) and reports how often each method agrees with the human label.
Writes recorded/judge_calibration_results.csv.

    python calibrate_judge.py                # cache only, no API key
    JUDGE_LIVE=1 python calibrate_judge.py   # fill missing verdicts from the API
"""

import csv
import json
import re
import sys
from pathlib import Path

from judge import JUDGE_MODEL, judge

HERE = Path(__file__).resolve().parent


def regex_verdict(case, answer):
    """Apply the regex assertions of the matching eval case (Python re, same patterns)."""
    for a in case["assert"]:
        if a["type"] == "regex" and not re.search(a["value"], answer):
            return "FAIL"
    return "PASS"


def main():
    cases = {c["vars"]["case_id"]: c for c in
             (json.loads(l) for l in (HERE / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    rows = [json.loads(l) for l in (HERE / "judge_calibration.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    out = []
    for r in rows:
        j = judge(r["answer"])
        rx = regex_verdict(cases[r["case_id"]], r["answer"])
        suite = "PASS" if rx == "PASS" and j["verdict"] == "PASS" else "FAIL"
        flag = "" if suite == r["human_label"] else "  <-- disagrees"
        out.append({**r, "regex": rx, "judge": j["verdict"], "suite": suite, "judge_reason": j["reason"]})
        print(f"{r['id']}  human {r['human_label']:<4}  regex {rx:<4}  judge {j['verdict']:<5}  suite {suite}{flag}", flush=True)

    with open(HERE / "recorded" / "judge_calibration_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "source", "case_id", "locale", "human_label", "regex", "judge", "suite",
                                          "note", "judge_reason", "answer"])
        w.writeheader()
        w.writerows({k: o[k] for k in w.fieldnames} for o in out)

    n = len(out)
    print(f"\nJudge: {JUDGE_MODEL}   answers: {n}")
    for method in ("regex", "judge", "suite"):  # suite = regex AND judge, as in eval_cases.jsonl
        agree = sum(o[method] == o["human_label"] for o in out)
        fp = sum(o[method] == "PASS" and o["human_label"] == "FAIL" for o in out)
        fn = sum(o[method] == "FAIL" and o["human_label"] == "PASS" for o in out)
        print(f"{method:<6} agrees {agree}/{n}   passes a bad answer: {fp}   fails a good answer: {fn}")
    sys.exit(1 if any(o["judge"] == "ERROR" for o in out) else 0)


if __name__ == "__main__":
    main()
