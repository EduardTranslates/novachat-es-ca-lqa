# ES/CA LQA Regression Checker

> **Synthetic data only.** All strings are fabricated for the fictional "NovaChat" product. No client or platform content.

A small Python script that automates the mechanical part of LQA for Spanish (es-ES) and Catalan (ca-ES) UI strings. It implements the regression tests proposed in the [NovaChat LQA case study](../README.md), so the linguist's time goes to what a script cannot judge: tone, meaning, and cultural fit.

Standard library only. No installs needed.

## Quick start

```bash
python lqa_checks.py        # reads sample_strings.csv, writes qa_report.csv
python test_lqa_checks.py   # runs the unit tests
```

## What it checks

| Check | MQM category | Severity | Example caught |
|---|---|---|---|
| Placeholder mismatch (`{count}`, `%s`, `{date}`) | Accuracy | Major | `{count}` → `{cuont}`; `%s` dropped |
| UI length limit | UX clarity | Major | 72 chars in a 50-char error banner |
| Gendered generics (inclusive policy) | Cultural / dialectal appropriateness | Major | ES "Bienvenido", CA "Benvingut" |
| Untranslated string | Accuracy | Major | "Upgrade" left in English |
| Glossary compliance | Terminology | Minor | "Configuración" instead of "Ajustes" |
| ES inverted punctuation | Fluency | Minor | "Quieres cancelar…?" without "¿" |
| CA punt volat | Fluency | Minor | "intel.ligència" → "intel·ligència" |
| CA Castilianisms | Cultural / dialectal appropriateness | Major | "recurso" instead of "recurs" |
| CA obsolete diacritics (IEC 2016 reform) | Fluency | Minor | "vés" instead of "ves" |
| Whitespace | Fluency | Minor | Double spaces, trailing spaces |

## Sample run

```
Strings checked: 20 | Issues: 14 | Strings with issues: 12
  Critical 0
  Major    7
  Minor    7
```

The sample set has 12 strings with seeded defects and 8 clean strings. All 12 were caught, with no false positives on the clean strings.

Severities follow the default severity per MQM category in the case study's quality framework. No Critical issues is expected: in the [full defect log](../defect_log.csv), all 3 Critical defects are hallucinations in AI responses, which string checks cannot see. Across the full defect log, these rules cover 17 of the 28 defects (61%), specifically those whose `auto_check` column names a checker rule. This is a coverage mapping, not a CLI run against `defect_log.csv`: the checker expects the schema in `sample_strings.csv`, including `id`, `source`, `target` and `max_chars`.

## A bug worth documenting

The first version of the glossary check used a plain substring match. The Catalan target "Configuración" (a Castilianism) **passed** the glossary check because it contains the approved term "Configuració". Switching to a word-boundary regex fixed it. That is a typical ES/CA trap: the two languages are close enough that naive string matching produces false negatives.

## What it does NOT catch

This is deliberate. A script can verify form; it cannot verify meaning.

- Mistranslations that are grammatically correct.
- Tone and register (e.g. passive "ha sido cancelada" vs. the brand's active voice).
- Hallucinated facts in AI responses (navigation paths, refund policies). Those are covered by the Promptfoo eval set in [`../evals/`](../evals/).

## Files

| File | Purpose |
|---|---|
| `lqa_checks.py` | The checker (one function per check, easy to extend) |
| `sample_strings.csv` | 20 synthetic UI strings (ES/CA) |
| `glossary.csv` | Approved EN → ES/CA terms |
| `rules.json` | Gendered terms, Castilianisms, obsolete diacritics, allow list (shared with `evals/`) |
| `qa_report.csv` | Generated output |
| `test_lqa_checks.py` | Unit tests |

*Author: Eduard Aliod Gil. Self-initiated portfolio project, November 2026.*
