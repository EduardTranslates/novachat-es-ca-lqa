"""
recorded_provider.py - Replays recorded model answers saved by record_responses.py.

No API key needed: grading is fully reproducible from recorded/responses.json.
Config: run = the run label used in record_responses.py.
"""

import json
from pathlib import Path

DATA = json.loads(
    (Path(__file__).resolve().parent / "recorded" / "responses.json").read_text(encoding="utf-8")
)


def call_api(prompt, options, context):
    run = options.get("config", {}).get("run")
    case_id = context.get("vars", {}).get("case_id")
    try:
        return {"output": DATA[run]["responses"][case_id]}
    except KeyError:
        return {"error": f"No recorded answer for run={run!r}, case_id={case_id!r}"}
