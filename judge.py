"""
judge.py - Model-graded check for the partial-month refund policy (EC-005, EC-006).

Why: the regex checks for these two cases look for a negation near "refund".
"No te preocupes: te devolveremos la parte proporcional" passes them, although
it promises the opposite of the policy. Meaning needs a reader, so a second
model reads the answer against a written rubric.

Design choices:
  - Judge model: gemini-3.5-flash, a different model from the ones that write
    the answers (3.5 Flash-Lite, 3.8 Flash, Nemotron 3 Ultra, ERNIE 5.5 Flash),
    so no model grades itself.
  - The rubric lives in this file, under version control, instead of Promptfoo's
    built-in llm-rubric template, so it can be read, reviewed and diffed.
  - Verdicts are cached in recorded/judge_verdicts.json, keyed by a hash of
    model + full judge prompt. Grading is reproducible offline, and editing the
    rubric invalidates the cache instead of silently reusing old verdicts.
  - Calibration against human labels: see calibrate_judge.py.

Modes:
  default        cache only; a missing verdict fails with a clear message
  JUDGE_LIVE=1   call the Gemini API on a cache miss and save the verdict
                 (needs GEMINI_API_KEY or an auth-injecting proxy)
"""

try:
    import fcntl
except ImportError:  # Windows: offline replay must not depend on a Unix module.
    fcntl = None
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent
CACHE = HERE / "recorded" / "judge_verdicts.json"
JUDGE_MODEL = "gemini-3.5-flash"

RUBRIC = """You review customer-support answers for NovaChat, a chat app.
The user asked: "If I cancel today, do I get back the part of the month I have not used?"

Official policy:
- After cancelling, access continues until the end of the current billing period.
- Partial months are not refunded.

Decide whether the ANSWER complies with the policy on partial-month refunds.

PASS only if all three are true:
1. It tells the user they will not get money back for the unused part, in any wording.
2. It does not promise, suggest or leave open any refund, credit, discount, proration
   or exception. "Contact support and we will review your case" leaves it open: FAIL.
3. It does not contradict itself.

Ignore language, spelling, tone, greetings and length, and whether it mentions
menu paths or access until the end of the period: other checks cover those.
Pointing the user to support for general questions is fine.
The answer may be in Spanish or Catalan.

Return JSON only: {"verdict": "PASS" or "FAIL", "reason": "<one sentence in English>"}"""


def build_prompt(answer):
    return f"{RUBRIC}\n\n<answer>\n{answer}\n</answer>"


def _key(prompt):
    return hashlib.sha256(f"{JUDGE_MODEL}\n{prompt}".encode("utf-8")).hexdigest()[:16]


def _load():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


@contextmanager
def _cache_lock():
    """Lock across processes on Unix and Windows; keep offline imports portable."""
    CACHE.parent.mkdir(exist_ok=True)
    with open(CACHE.with_suffix(".lock"), "a+b") as lock:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        else:
            import msvcrt
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock, fcntl.LOCK_UN)
            else:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def _save(key, entry):
    """Merge under a lock, then atomically replace so readers see complete JSON."""
    with _cache_lock():
        data = _load()
        data[key] = entry
        tmp = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=CACHE.parent,
                                    suffix=".tmp", delete=False) as f:
                tmp = Path(f.name)
                f.write(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            os.replace(tmp, CACHE)
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink()


def judge(answer):
    """Return {"verdict": "PASS"|"FAIL"|"ERROR", "reason": str, "cached": bool}."""
    prompt = build_prompt(answer)
    key = _key(prompt)
    cached = _load().get(key)
    if cached:
        return {"verdict": cached["verdict"], "reason": cached["reason"], "cached": True}
    if os.environ.get("JUDGE_LIVE") != "1":
        return {"verdict": "ERROR", "cached": False,
                "reason": f"No cached verdict ({key}). Re-run with JUDGE_LIVE=1 and an API key."}

    from gemini_provider import call_api  # imported here: cache-only mode needs no requests
    result = call_api(json.dumps([{"role": "user", "content": prompt}]),
                      {"config": {"model": JUDGE_MODEL, "temperature": 0,
                                  "response_mime_type": "application/json"}}, {})
    if "error" in result:
        return {"verdict": "ERROR", "reason": result["error"][:200], "cached": False}
    try:
        parsed = json.loads(result["output"])
        verdict = str(parsed["verdict"]).strip().upper()
        reason = str(parsed["reason"]).strip()
        assert verdict in ("PASS", "FAIL")
    except (ValueError, KeyError, TypeError, AssertionError):
        return {"verdict": "ERROR", "reason": f"Unparseable judge output: {result['output'][:200]}",
                "cached": False}
    _save(key, {"model": JUDGE_MODEL, "verdict": verdict, "reason": reason, "answer": answer})
    return {"verdict": verdict, "reason": reason, "cached": False}


def partial_refund_judge(output, context):
    """Promptfoo assertion: file://judge.py:partial_refund_judge"""
    result = judge(output)
    return {"pass": result["verdict"] == "PASS",
            "score": 1.0 if result["verdict"] == "PASS" else 0.0,
            "reason": f"Judge ({JUDGE_MODEL}) {result['verdict']}: {result['reason']}"}
