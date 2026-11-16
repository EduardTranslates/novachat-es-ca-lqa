"""
record_responses.py - Call each model once per case and save the answers to disk.

Why: free-tier latency is high and variable, so the suite is split in two steps.
  1. Record:  python record_responses.py [run label filter]
              (needs GEMINI_API_KEY for Gemini runs, OPENROUTER_API_KEY for OpenRouter runs)
  2. Grade:   npx promptfoo@latest eval -c promptfooconfig.recorded.yaml
Step 2 needs no API key, so anyone can reproduce the grading from the saved answers.

Runs: each (prompt variant, model) pair below. Output: recorded/responses.json
"""

import json
import sys
import time
from pathlib import Path

import yaml  # pip install pyyaml

import gemini_provider
import openrouter_provider

HERE = Path(__file__).resolve().parent
OUT = HERE / "recorded" / "responses.json"

RUNS = [
    # (run label, prompt file, model, provider)
    ("grounded / gemini-3.5-flash-lite", "prompt.yaml", "gemini-3.5-flash-lite", "gemini"),
    ("grounded / gemini-3.8-flash", "prompt.yaml", "gemini-3.8-flash", "gemini"),
    ("baseline / gemini-3.5-flash-lite", "prompt_baseline.yaml", "gemini-3.5-flash-lite", "gemini"),
    # Non-Google models through OpenRouter (free tier), same grounded prompt.
    ("grounded / nemotron-3-ultra", "prompt.yaml", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter"),
    ("grounded / ernie-5.5-flash", "prompt.yaml", "baidu/ernie-5.5-flash-preview:free", "openrouter"),
]
PROVIDERS = {"gemini": gemini_provider.call_api, "openrouter": openrouter_provider.call_api}


def render(prompt_file, question):
    messages = yaml.safe_load((HERE / prompt_file).read_text(encoding="utf-8"))
    for m in messages:
        m["content"] = m["content"].replace("{{question}}", question)
    return json.dumps(messages, ensure_ascii=False)


def main():
    cases = [json.loads(l) for l in (HERE / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}

    runs = [r for r in RUNS if len(sys.argv) < 2 or sys.argv[1] in r[0]]
    for label, prompt_file, model, provider in runs:
        run = data.setdefault(label, {"prompt": prompt_file, "model": model, "responses": {}})
        for case in cases:
            cid = case["vars"]["case_id"]
            if cid in run["responses"]:
                continue  # resume: skip answers already recorded
            started = time.time()
            result = PROVIDERS[provider](render(prompt_file, case["vars"]["question"]),
                              {"config": {"model": model, "temperature": 0}}, {})
            status = "ok" if "output" in result else result["error"][:80]
            print(f"{label:<36} {cid}  {time.time() - started:5.1f}s  {status}", flush=True)
            if "output" in result:
                run["responses"][cid] = result["output"]
                OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    missing = sum(len(cases) - len(data[r[0]]["responses"]) for r in runs)
    print(f"Done. Missing answers: {missing}", flush=True)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
