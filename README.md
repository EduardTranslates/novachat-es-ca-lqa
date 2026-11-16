# ES/CA Eval Set for an AI Support Assistant (Promptfoo)

> **Synthetic data only.** Questions, answers, policies and menu paths belong to the fictional "NovaChat" product. No client or platform content.

A regression suite for the AI-response defects found in the [NovaChat LQA case study](../README.md). The [string checker](../lqa-checker/) covers UI strings; this suite covers what it cannot see: hallucinated menu paths, invented policy details and language switching in generated answers.

It runs offline, with no API key, against mock answers. It has also been run against four real models (two Gemini, plus NVIDIA Nemotron 3 Ultra and Baidu ERNIE 5.5 Flash through OpenRouter), with every answer reviewed: see **[RESULTS.md](RESULTS.md)** for what it found.

## Quick start

```bash
npx promptfoo@latest eval                                   # suite vs mock answers (from this folder)
npx promptfoo@latest eval -c promptfooconfig.recorded.yaml  # suite vs recorded real answers (4 models)
npx promptfoo@latest view                                   # browse results in the web viewer
python test_assertions.py                                   # unit tests for the Python assertions
python test_judge_portability.py                            # cache, portable import and CLI smoke tests
python calibrate_judge.py                                   # refund judge vs regex vs human labels
```

Neither eval needs an API key.

The Python checks and cached judge replay need no network. The first `npx` invocation needs Internet to install Promptfoo. For the tested version, replace `promptfoo@latest` with `promptfoo@0.121.20`. Judge cache writes use `fcntl` on Unix and `msvcrt` on Windows; the Windows branch has simulated unit coverage, not a native Windows validation run.

Requires Python 3 and a Node.js version supported by Promptfoo (see the [installation guide](https://www.promptfoo.dev/docs/installation/)). Built and run with Promptfoo 0.121.20.

Run one locale only: `npx promptfoo@latest eval --filter-metadata locale=ca-ES`

## How it is built

| Layer | File | What it does |
|---|---|---|
| System prompt | `prompt.yaml` | The source of truth: UI map, glossary and policies for both locales. This is the P0 fix from the case study. |
| Test cases | `eval_cases.jsonl` | 12 cases, one JSON object per line: a user question plus fact and policy assertions. |
| Model-graded check | `judge.py` | EC-005/006 only: a second model (`gemini-3.5-flash`) checks the answer against a written refund rubric. Verdicts are cached, so it runs offline. |
| Global checks | `promptfooconfig.yaml` → `assertions.py` | Four linguistic checks applied to every answer: stays in the user's language, informal register, no masculine generics, Catalan orthography (Castilianisms such as "Ajustes" or "disfruta", pre-2016 diacritics such as "vés"). |

Each line of `eval_cases.jsonl` looks like this (wrapped here for reading):

```json
{"description": "EC-004 | ca-ES | Refund timeframe",
 "vars": {"case_id": "EC-004", "locale": "ca-ES",
          "question": "He demanat un reemborsament. Quan el rebré?"},
 "assert": [
   {"type": "regex", "value": "(14|catorze) dies feiners", "metric": "policy"},
   {"type": "python", "value": "file://assertions.py:day_figures_match_policy",
    "config": {"allowed_days": [14]}, "metric": "policy"}],
 "metadata": {"locale": "ca-ES", "intent": "Refund timeframe",
              "risk": "Critical", "linked_defects": ["D-005"]}}
```

## The 12 cases

| ID | Locale | What it tests | Defect | Risk |
|---|---|---|---|---|
| EC-001 | es-ES | Downgrade path must be Ajustes > Suscripción | D-002 | Critical |
| EC-002 | ca-ES | Downgrade path must be Configuració > Subscripció | D-002 | Critical |
| EC-003 | es-ES | Refund timeframe is 14 business days, no other figure | D-005 | Critical |
| EC-004 | ca-ES | Refund timeframe is 14 business days, no other figure | D-005 | Critical |
| EC-005 | es-ES | No refund for partial months after cancelling | D-006 | Critical |
| EC-006 | ca-ES | No refund for partial months after cancelling | D-006 | Critical |
| EC-007 | ca-ES | Answer stays in Catalan from start to end | D-021 | Major |
| EC-008 | es-ES | Adversarial: user asserts a false "2 days" refund and asks for confirmation | D-005 | Critical |
| EC-009 | ca-ES | Out of scope: must not invent a student discount | new | Critical |
| EC-010 | es-ES | Out of scope: must not invent a price | new | Critical |
| EC-011 | es-ES | Onboarding: neutral greeting, "tú", glossary term | D-003, D-016, D-017 | Major |
| EC-012 | ca-ES | Onboarding: neutral greeting, "tu", glossary term | D-019, D-026 | Major |

Every assertion carries a `metric` (`hallucination`, `policy`, `cultural_dialectal`, `tone`, `terminology`, `fluency`) that maps to the MQM categories of the case study, so results can be read per category.

## Testing the tests

The suite is validated against three sets of hand-written answers (`mock_responses.json`), re-run after every change to the assertions:

| Mock answers | What they are | Expected | Result |
|---|---|---|---|
| `mock-defective` | The faulty answers from `defect_log.csv` | 0/12 pass | 0/12 pass |
| `mock-fixed` | The corrected answers | 12/12 pass | 12/12 pass |
| `mock-fixed-variant` | Correct answers worded differently: longer, Markdown bold, arrows, typographic apostrophes | 12/12 pass | 12/12 pass |

The first row shows the assertions are strict enough to catch each known defect, and each case fails for the intended reason. The third shows they are not so strict that a correct answer fails because of its wording.

Real answers still found five gaps the mocks had not (three in the Gemini runs, two more in the cross-vendor run). They are described in [RESULTS.md](RESULTS.md), fixed, and covered by regression checks built from the real output.

## Three traps worth documenting

1. **JavaScript regex does not understand accents.** Promptfoo's built-in `regex` runs in JavaScript, where `\b` and `\w` are ASCII-only: `\bvostè\b` does not match "Pot vostè canviar-ho". All checks on accented ES/CA words are therefore written in Python (`assertions.py`), where the same pattern works.
2. **Typographic apostrophes.** A `contains "servei d'assistència"` check fails when the model writes `d’assistència` with a curly apostrophe, which models often do. The assertion accepts both.
3. **UI rules do not transfer to free text.** The string checker flags "registrado" as a masculine generic. In a generated answer, "el correo registrado" is correct. The eval set uses a narrower list (greetings only), kept in the same `rules.json`.

## Limits

- **Small sample.** 12 cases, 4 models, 1 or 2 runs each. The real runs show how the suite behaves; they are not a benchmark.
- **Temperature 0 is not deterministic.** The same case passed in one run and failed in another. One passing run proves little.
- **Rules miss what nobody listed.** Human review of the real answers found Catalan errors no assertion flagged (for example "se'te cobrarà" for "se't cobrarà"). See [RESULTS.md](RESULTS.md).
- **Deterministic assertions check form, not meaning.** "No te preocupes: te devolveremos la parte proporcional" passed the old refund regex. EC-005 and EC-006 now use a model-graded check, calibrated at 20/20 against human labels on a small set written by the same person who wrote the rubric (see [RESULTS.md](RESULTS.md)). The other cases are still rule-based.
- **The judge only sees cached answers offline.** A new answer needs `JUDGE_LIVE=1` and an API key; without them the check fails with a clear message instead of passing silently.
- **The language check is a word-list heuristic** (function words that exist in one language but not the other). It catches a switch such as D-021; it is not a language identifier.
- **The register check only sees explicit forms** ("usted", "su perfil", "vostè", "el seu compte"). A bare formal imperative ("Configure") is not detected.

## Running against a real model

Free-tier latency is high and variable, so recording and grading are separate steps:

1. **Record.** `python record_responses.py [label filter]` calls each prompt and model in `RUNS` once per case, and saves the answers to `recorded/responses.json`. Gemini runs need `GEMINI_API_KEY`, OpenRouter runs `OPENROUTER_API_KEY`; both need `pip install requests pyyaml`. Example: `python record_responses.py ernie` records only the ERNIE run. It is resumable: cases already recorded are skipped, so a quota error does not lose work.
2. **Grade.** `npx promptfoo@latest eval -c promptfooconfig.recorded.yaml` replays the saved answers through the same cases and assertions. No key needed.

`gemini_provider.py` and `openrouter_provider.py` can also be used directly as Promptfoo providers (`id: file://openrouter_provider.py`, `config: {model: ...}`). Both retry on 429 and 5xx errors. OpenRouter gives access to models from many vendors with one key, which is how the cross-vendor check was run.

To measure the effect of the grounded prompt, `prompt_baseline.yaml` keeps the style rules but removes the UI map, glossary and policies.

## Files

| File | Purpose |
|---|---|
| `eval_cases.jsonl` | The 12 test cases |
| `promptfooconfig.yaml` | Suite config: prompt, mock providers, global checks |
| `promptfooconfig.recorded.yaml` | Same suite, graded on the recorded answers of all 4 models |
| `prompt.yaml` | System prompt with UI map, glossary and policies |
| `prompt_baseline.yaml` | Same prompt without UI map, glossary or policies |
| `assertions.py` | Python assertions for language, register, inclusive language, Catalan orthography and day figures |
| `test_assertions.py` | Unit tests for the assertions |
| `test_judge_portability.py` | Offline import, cache locking, mock consistency and checker CLI tests |
| `mock_provider.py`, `mock_responses.json` | Offline mock answers (defective, fixed, fixed variant) |
| `gemini_provider.py` | Gemini API provider (retries, timeout) |
| `openrouter_provider.py` | OpenRouter provider, OpenAI-compatible chat completions (retries, timeout) |
| `record_responses.py` | Records real answers to `recorded/responses.json` |
| `recorded_provider.py`, `recorded/responses.json` | Replays the recorded answers |
| `judge.py` | Model-graded refund check, with cached verdicts |
| `judge_calibration.jsonl` | 20 human-labelled answers for calibrating the judge |
| `calibrate_judge.py`, `recorded/judge_calibration_results.csv` | Judge vs regex vs human, with results |
| `recorded/judge_verdicts.json` | Cached judge verdicts |
| `recorded/human_review.csv` | Automatic result and human verdict for all 72 recorded answers (4 models) |
| `RESULTS.md` | Results of the Gemini and OpenRouter runs, case-by-case review and judge calibration |

*Author: Eduard Aliod Gil. Self-initiated portfolio project, November 2026.*
