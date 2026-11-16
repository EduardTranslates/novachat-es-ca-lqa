"""
mock_provider.py - Offline stand-in for a real model, so the suite runs with no API key.

It returns canned answers from mock_responses.json in one of three modes:
  defective     -> the faulty answers documented in defect_log.csv (must FAIL)
  fixed         -> the corrected answers (must PASS)
  fixed_variant -> correct answers phrased differently (must PASS)

Purpose: test the tests. If a defective answer passes, the assertion is too weak.
If a correct but differently worded answer fails, it is too strict.
To evaluate a real model, replace this provider in promptfooconfig.yaml.
"""

import json
from pathlib import Path

RESPONSES = json.loads(
    (Path(__file__).resolve().parent / "mock_responses.json").read_text(encoding="utf-8")
)


def call_api(prompt, options, context):
    mode = options.get("config", {}).get("mode", "fixed")
    case_id = context.get("vars", {}).get("case_id")
    if case_id not in RESPONSES:
        return {"error": f"No mock response for case_id={case_id!r}"}
    return {"output": RESPONSES[case_id][mode]}
