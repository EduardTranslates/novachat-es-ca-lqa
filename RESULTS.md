# Results: NovaChat ES/CA Eval Set on Gemini and OpenRouter Models (November 2026)

> **Synthetic data only.** Fictional product, policies and menu paths. Answers are real API outputs (Gemini, plus two OpenRouter models in the [cross-vendor run](#cross-vendor-run-openrouter-16-november-2026)), saved in [`recorded/responses.json`](recorded/responses.json).

## Setup

| Item | Value |
|---|---|
| Suite | 12 cases (6 es-ES, 6 ca-ES), see [README](README.md) |
| Models | `gemini-3.5-flash-lite`, `gemini-3.8-flash` (Gemini API, free tier); cross-vendor check: Nemotron 3 Ultra, ERNIE 5.5 Flash (OpenRouter, free tier) |
| Temperature | 0 |
| Grounded prompt | [`prompt.yaml`](prompt.yaml): style rules + UI map + glossary + policies |
| Baseline prompt | [`prompt_baseline.yaml`](prompt_baseline.yaml): same style rules, **no** UI map, glossary or policies |
| Judge (EC-005/006) | `gemini-3.5-flash`, temperature 0, JSON output |
| Human review | All 72 answers (48 Gemini, 24 OpenRouter), by the author (bilingual ES/CA) |
| Date | 15-16 November 2026 (OpenRouter: 16 November) |

Reproduce the grading with no API key: `npx promptfoo@latest eval -c promptfooconfig.recorded.yaml`

## Summary

| Run | Passed | Failed | Missing |
|---|---|---|---|
| Baseline / gemini-3.5-flash-lite | 2 | **10** | 0 |
| Grounded / gemini-3.5-flash-lite (run 1) | 10 | 2 | 0 |
| Grounded / gemini-3.5-flash-lite (run 2) | 10 | 2 | 0 |
| Grounded / gemini-3.8-flash | **12** | 0 | 0 |
| Grounded / Nemotron 3 Ultra (OpenRouter) | 10 | 2 | 0 |
| Grounded / ERNIE 5.5 Flash (OpenRouter) | 12 | 0 | 0 |

`gemini-3.8-flash` EC-001, EC-003 and EC-007 failed first with HTTP 502 errors and then with the free-tier quota (20 requests per model per day). They were recorded on 16 November with a new key.

## Case-by-case review

Each cell shows **automatic result / human verdict**, with the severity of the worst defect a human reviewer would log. Flash-Lite #1 and #2 are the two grounded runs of 3.5 Flash-Lite; 3.8 Flash is also grounded; Baseline is 3.5 Flash-Lite without grounding. Every answer was read in full; the notes are in [`recorded/human_review.csv`](recorded/human_review.csv).

- **PASS / FAIL**: whether the answer is acceptable.
- **QUERY**: correct for what the source covers, but the answer adds a claim the source does not cover. In LQA practice this goes to the product owner, not straight into the defect log.
- **Bold**: the automatic result and the human verdict disagree.

| Case | Locale | Tests | Flash-Lite #1 | Flash-Lite #2 | 3.8 Flash | Baseline |
|---|---|---|---|---|---|---|
| EC-001 | es-ES | Downgrade path | PASS / QUERY | PASS / QUERY | PASS / PASS | FAIL / FAIL (Critical) |
| EC-002 | ca-ES | Downgrade path | PASS / QUERY | PASS / QUERY | PASS / PASS | FAIL / FAIL (Critical) |
| EC-003 | es-ES | Refund window | PASS / PASS | PASS / PASS | PASS / PASS | FAIL / FAIL (Critical) |
| EC-004 | ca-ES | Refund window | PASS / PASS | PASS / PASS | PASS / PASS | FAIL / FAIL (Critical) |
| EC-005 | es-ES | Partial-month refund | PASS / PASS | PASS / PASS | PASS / PASS | PASS / PASS |
| EC-006 | ca-ES | Partial-month refund | PASS / PASS | PASS / PASS | PASS / PASS | **PASS / FAIL (Minor)** |
| EC-007 | ca-ES | Stays in Catalan | FAIL / FAIL (Minor) | FAIL / FAIL (Minor) | PASS / PASS | FAIL / FAIL (Critical) |
| EC-008 | es-ES | False premise (2 days) | PASS / PASS | PASS / PASS | PASS / PASS | FAIL / FAIL (Critical) |
| EC-009 | ca-ES | Student discount (unknown) | PASS / PASS | PASS / PASS | PASS / PASS | FAIL / FAIL (Critical) |
| EC-010 | es-ES | Price (unknown) | PASS / PASS | PASS / PASS | PASS / PASS | FAIL / FAIL (Critical) |
| EC-011 | es-ES | Onboarding | PASS / PASS | PASS / PASS | PASS / PASS | FAIL / FAIL (Major) |
| EC-012 | ca-ES | Onboarding | FAIL / FAIL (Major) | FAIL / FAIL (Minor) | PASS / PASS | FAIL / FAIL (Major) |

**Agreement on pass/fail: 47 of 48 answers** (QUERY counted as pass). The one miss is baseline EC-006: correct policy, but "se'te cobrarà" instead of "se't cobrarà".

Agreeing on the verdict is not the same as agreeing on the reason. Baseline EC-012 failed automatically only because "espai de treball" was missing; the human review also found an invented bot, the masculine generic "encallat" and "Puja" for the glossary term "Penja". A pass rate hides this, so the defect types are listed below.

The 4 QUERY answers (EC-001 and EC-002, both grounded Flash-Lite runs) say that after a downgrade the user keeps access until the end of the period and gets no refund. The source states this only for cancelling. It is plausible, but it is a policy claim the model made up, the same kind of risk as D-006. The source document should say what happens on a downgrade.

### What the system detects and what needs a human

| Defect type | Example from these runs | Detected by |
|---|---|---|
| Invented menu path | "Facturación" o "Plan" (EC-001, baseline) | Automatic (regex) |
| Invented figure, price or discount | 5-10 days, 12 EUR, 50% (baseline) | Automatic (regex + Python) |
| Missing glossary term | No "espacio de trabajo" in onboarding (EC-011, baseline) | Automatic (contains) |
| Spanish menu name in Catalan | "Ajustes > Perfil" (EC-012, run 1) | Automatic (Python, word list) |
| Listed Castilianism | "Disfruta" (EC-007, baseline); "reembolsen" (EC-006, Nemotron) | Automatic (Python, word list) |
| Pre-2016 accent | "vés" (EC-007, EC-012) | Automatic (Python, word list) |
| Refund promised or left open | Synthetic traps JC-15 to JC-18; "Los reembolsos (si procede)…" (EC-005, Nemotron) | Model-graded judge |
| Grammar error | "se'te cobrarà" (EC-006, baseline); "escrivim" for "escriu" (EC-012, Nemotron) | **Human only** |
| Wrong word | "El descompte" for a plan change (EC-002, baseline) | **Human only** |
| Masculine generic outside greetings | "Si et quedes encallat" (EC-012, baseline) | **Human only** |
| Glossary term not in the case's checks | "Puja una foto" vs glossary "Penja" (EC-012, baseline) | **Human only** |
| Invented UI element in free text | A "Nuevo chat" button (EC-011, baseline) | **Human only** |
| Dialectal consistency | Valencian "teua" next to central forms (EC-002, EC-007, baseline) | **Human only** |
| Regional variety | "Qué bueno tenerte por aquí" (EC-011, run 1) | **Human only** (preferential) |
| Policy extended beyond the source | Cancellation rules applied to a downgrade (EC-001/002, Flash-Lite); invented downgrade timing (EC-001/002, Nemotron) | **Human only** |

The automatic checks catch what can be written as a list: paths, figures, terms, known word forms. A human catches the rest: grammar, meaning, consistency and claims nobody anticipated. The model-graded judge sits in between, and only for the one policy it has a rubric for.

## Key findings

### 1. Grounding removes the hallucinations

Without the UI map and policies, the model invents what it does not know. With them, every Critical hallucination of the baseline disappears across all four models. (Nemotron still fails the two Critical-risk refund cases, EC-005 and EC-006, on wording rather than invented facts: see the [cross-vendor run](#cross-vendor-run-openrouter-16-november-2026).)

| Case | Baseline answer (excerpt) | What is wrong |
|---|---|---|
| EC-009 | "Sí, tenim un descompte del 50% per a estudiants en tots els nostres plans." | Invented discount |
| EC-010 | "El plan Pro cuesta 12 € al mes (o 10 € al mes si pagas de forma anual)." | Invented prices |
| EC-003 | "El reembolso suele tardar entre 5 y 10 días laborables…" | Policy says up to 14 business days |
| EC-008 | "No, normalmente tardan entre 5 y 10 días laborables…" | Rejects the false premise, then invents another figure |
| EC-001 | "…ve a la configuración de tu cuenta, entra en la sección de "Facturación" o "Plan"…" | Invented menu path (same pattern as defect D-002) |
| EC-007 | "…fes clic a la teua foto o icona d'usuari a baix a l'esquerra…" | Invented UI layout |

This supports P0 in the case study: the fix for hallucinated paths and policies is in the system prompt, not in the translation.

### 2. Grounding does not fix the language

The grounded Flash-Lite runs pass every fact and policy check, yet 2 of 12 still fail on Catalan in each run:

- **Pre-2016 accent:** "vés a Configuració > Idioma" (EC-007, both runs; EC-012, run 2). The 2016 IEC spelling reform removed this diacritic: the standard form is "ves" ([Optimot](https://aplicacions.llengua.gencat.cat/llc/AppJava/index.html?method=detall&input_cercar=%22ves%22&numPagina=1&database=FITXES_PUB&idFont=14591&titol=El+mot+%3Cem%3Eves+%3C/em%3Eporta+accent+diacr%EDtic?&tipusCerca=cerca.queSignifica); [IEC](https://www.iec.cat/llengua/documents/ORTOGRAFIA-Presentaci%C3%B3.pdf)). Minor, but systematic.
- **Spanish menu path in a Catalan answer:** "completar el teu perfil (Ajustes > Perfil)" (EC-012, run 1). The answer is otherwise correct Catalan, but it points to a menu that does not exist in the Catalan UI. This is the D-021 pattern (Spanish interference) in its subtlest form.

### 3. The larger model also gets the Catalan right

`gemini-3.8-flash` with the grounded prompt passed all 12 cases. Where Flash-Lite wrote "vés a Configuració > Idioma", 3.8 Flash wrote "Pots canviar l'idioma anant a Configuració > Idioma", which avoids the imperative altogether. In this sample, grounding fixes the facts and the larger model fixes the remaining language errors. With 12 cases and one run, this is a lead to test, not a conclusion.

### 4. Temperature 0 is not deterministic

Same model, prompt and temperature, two runs: EC-012 contained "Ajustes > Perfil" in run 1 and not in run 2. A single passing run proves little. Regression suites for LLMs need repeated runs.

### 5. Real answers broke the suite three times

Each one is fixed and covered by a unit test built from the real output:

| Problem | Real answer | Type | Fix |
|---|---|---|---|
| "Ajustes" in a Catalan answer passed | EC-012, run 1 | False negative | Spanish menu names added to the Castilianism list; Catalan menu names blocked in Spanish answers |
| "entre 5 y 10 días" read as only "10" | EC-003, baseline | False negative | "y" / "e" added as connectors in the day-figure regex |
| Correct answer failed: "fins que s'acabi el període que ja has pagat" | EC-006, baseline | False positive | Accepts "període que has pagat" as well as "període de facturació" |

Plus two new rules: obsolete diacritics (`vés`, `dóna`, `sóc`…) and "disfruta" as a Castilianism. Both are shared with the [string checker](../lqa-checker/).

### 6. A second vendor breaks a suite tuned on one

Run on Nemotron 3 Ultra and ERNIE 5.5 Flash, the same suite produced two false negatives and missed one Castilianism that four Gemini runs had never triggered. Details in the [cross-vendor run](#cross-vendor-run-openrouter-16-november-2026).

## Human review: errors no assertion flagged

Problems found by reading the baseline answers that no assertion flagged:

| Answer (excerpt) | Issue | Category |
|---|---|---|
| "No se'te cobrarà res més" (EC-006) | Wrong clitic: "se't" | Fluency |
| "El descompte s'aplicarà en el pròxim cicle" (EC-002) | Says "discount" for a plan change | Accuracy |
| "vés a la teua configuració" (EC-002, EC-007) | Valencian "teua" in a product that uses central "teu/teva" | Cultural / dialectal (inconsistency, not an error) |
| "¡Qué bueno tenerte por aquí!" (EC-011, grounded run 1) | More typical of Latin American Spanish; es-ES would say "Qué bien" | Cultural / dialectal (Minor, debatable) |

Each could become a rule, but the list would never be complete. That is the case for model-graded checks, calibrated against a human reviewer. The first one, for the refund policy, is below.

## Model-graded check: partial-month refunds (EC-005, EC-006)

The regex checks for EC-005 and EC-006 looked for a negation near "refund". They passed every real answer, but they read form, not meaning. A second model now reads each answer against a written rubric: no money back for the unused part, no refund, credit or exception left open, and no self-contradiction ([`judge.py`](judge.py)).

| Choice | Why |
|---|---|
| Judge: `gemini-3.5-flash` | Not one of the models that write the answers, so no model grades itself |
| Own rubric instead of Promptfoo's `llm-rubric` | The rubric is in the repo, under version control |
| Verdicts cached in [`recorded/judge_verdicts.json`](recorded/judge_verdicts.json) | Grading runs offline; editing the rubric invalidates the cache |
| JSON output, temperature 0 | One parseable verdict and reason per answer |

### Calibration against human labels

[`judge_calibration.jsonl`](judge_calibration.jsonl) has 20 answers, each labelled PASS or FAIL by a human reviewer: the 6 mock answers, the 8 real Gemini answers and 6 synthetic traps written to break the regex. Run `python calibrate_judge.py`.

| Method | Agrees with human | Passes a bad answer | Fails a good answer |
|---|---|---|---|
| Old regex pair | 14/20 | 4 | 2 |
| Judge | **20/20** | 0 | 0 |
| Current period regex alone | 16/20 | 4 | 0 |
| Current suite (period regex + judge) | 20/20 | 0 | 0 |

The 4 bad answers the regex passed:

| ID | Answer (excerpt) | Trap |
|---|---|---|
| JC-15 | "No te preocupes: te devolveremos la parte proporcional del mes." | Opens with a negation, then promises a refund |
| JC-16 | "No hi ha reemborsament…, però t'afegirem un crèdit pels dies no utilitzats." | A refund by another name |
| JC-17 | "Normalmente no hacemos reembolsos…, pero si escribes a soporte podemos revisar tu caso." | Leaves an exception open |
| JC-18 | "No es reemborsen els mesos parcials. De tota manera, … et tornarem els dies que no hagis fet servir…" | Contradicts itself |

The two good answers the regex failed (JC-19, JC-20) said "fecha de renovación" / "data de renovació" instead of "billing period". The negation regex was removed; the period regex now accepts those phrasings. That is why `calibrate_judge.py`, which applies the current regexes from `eval_cases.jsonl`, reports 16/20 for the regex: the 2 false negatives are fixed, the 4 false positives remain, and only the judge catches them.

### How much to trust 20/20

- **The same person wrote the rubric and the traps.** The rubric names the "contact support" pattern that JC-17 tests. Traps written by someone else would be a fairer test.
- **20 answers, 6 of them bad.** Enough to show the regex failure mode, not enough to estimate the judge's error rate.
- **Stability:** JC-15 and JC-16 were judged a second time with no cache and got the same verdict. The other repeats hit the daily free-tier quota.
- **Same vendor in the calibration set.** The only real model answers in the calibration set come from Gemini, and so does the judge. The cross-vendor run below tests the judge on Nemotron and ERNIE, though using a non-Gemini judge would also rule out judge-side blind spots.


## Cross-vendor run: OpenRouter (16 November 2026)

Same grounded prompt and 12 cases, two non-Google models through OpenRouter's free tier, temperature 0. Answers are in `recorded/responses.json` and are graded with the same offline config. The refund judge (gemini-3.5-flash) grades EC-005 and EC-006, so no answer model grades itself.

| Model | Automatic | Human | Failures |
|---|---|---|---|
| NVIDIA Nemotron 3 Ultra (`nvidia/nemotron-3-ultra-550b-a55b:free`) | 10/12 | 9/12 | EC-005 refund left open; EC-006 Castilianism; EC-012 grammar (missed by the suite) |
| Baidu ERNIE 5.5 Flash (`baidu/ernie-5.5-flash-preview:free`) | 12/12 | 12/12 | None found |

Each cell shows **automatic result / human verdict**, as in the Gemini table. Every answer was read in full; the notes are in [`recorded/human_review.csv`](recorded/human_review.csv) with the Gemini verdicts. QUERY is counted as pass.

| Case | Tests | Nemotron 3 Ultra | ERNIE 5.5 Flash |
|---|---|---|---|
| EC-001 | Downgrade path | PASS / QUERY | PASS / PASS |
| EC-002 | Downgrade path | PASS / QUERY | PASS / PASS |
| EC-003 | Refund window | PASS / PASS | PASS / PASS |
| EC-004 | Refund window | PASS / PASS | PASS / PASS |
| EC-005 | Partial-month refund | FAIL / FAIL (Major) | PASS / PASS |
| EC-006 | Partial-month refund | FAIL / FAIL (Minor) | PASS / PASS |
| EC-007 | Stays in Catalan | PASS / PASS | PASS / PASS |
| EC-008 | False premise (2 days) | PASS / PASS | PASS / PASS |
| EC-009 | Student discount (unknown) | PASS / PASS | PASS / PASS |
| EC-010 | Price (unknown) | PASS / PASS | PASS / PASS |
| EC-011 | Onboarding | PASS / PASS | PASS / PASS |
| EC-012 | Onboarding | **PASS / FAIL (Minor)** | PASS / PASS |

**Agreement on pass/fail: 23 of 24 answers.** The miss is Nemotron EC-012: "Si tens qualsevol dubte, escrivim al servei d'assistència". "Escrivim" means "we write"; the imperative is "escriu al servei d'assistència". A grammar error, like the Gemini miss ("se'te cobrarà"): the pattern holds across vendors.

The two QUERY answers (Nemotron EC-001 and EC-002) add when a downgrade takes effect ("El cambio se aplicará al final del periodo de facturación actual"; "El canvi s'aplicarà al proper cicle de facturació"). The source says nothing about it. This is the same open question Flash-Lite raised in a different form: the source document should define what happens on a downgrade.

What a new model family broke:

| Problem | Real answer | Type | Fix |
|---|---|---|---|
| "14 días hábiles" written with a narrow no-break space (U+202F) failed the timeframe regex | EC-003 and EC-008, Nemotron | False negative | Timeframe regexes use `\s+` instead of a literal space (EC-003, EC-004, EC-008) |
| "els mesos parcials no es reembolsen" passed the Catalan checks | EC-006, Nemotron | Missed error | `reembolsar` and its forms added to the Castilianism list (correct form: `reemborsar`), shared with the string checker; unit test from the real output |

Neither problem appeared in four Gemini runs. A suite tuned on one model family carries that family's habits, in typography as well as wording.

The judge on the four new answers: Nemotron EC-005 FAIL ("Los reembolsos (si procede) se tramitan en un máximo de 14 días hábiles" leaves a refund open after saying there is none); the other three PASS. That matches the review. No regex would catch a refund left open by a parenthesis, so this answer is a good candidate for the next calibration set.

## Limits

- 12 cases, 4 models (2 Gemini, 2 through OpenRouter), 1 or 2 runs per configuration. These results show how the suite works; they are not a model benchmark.
- The OpenRouter models were run once each, on free-tier endpoints whose serving setup may change.
- Free tier: high, variable latency (1 s for Flash-Lite, 30-90 s for 3.8 Flash) and a daily quota of 20 requests per model.
- The mock answers ([`mock_responses.json`](mock_responses.json)) are still the regression test for the suite itself: 0/12 defective, 12/12 fixed, 12/12 fixed-variant pass after all the changes above.

*Author: Eduard Aliod Gil. Self-initiated portfolio project, November 2026.*
