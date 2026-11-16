"""
lqa_checks.py - Automated LQA regression checks for ES/CA UI strings.

Implements the regression tests proposed in the NovaChat LQA case study
(synthetic data only). Standard library only: no installs needed.

Severities follow the default severity per MQM category defined in the case
study's quality framework. A reviewer can raise or lower them per defect.

Usage:
    python lqa_checks.py                       # uses the default sample files
    python lqa_checks.py --strings my.csv --out my_report.csv
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Placeholders: ICU-style {name} and printf-style %s / %d / %1$s
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}|%(?:\d+\$)?[sd]")


def find_placeholders(text):
    return sorted(PLACEHOLDER_RE.findall(text))


def issue(row, check, category, severity, message):
    return {
        "id": row["id"],
        "locale": row["locale"],
        "check": check,
        "mqm_category": category,
        "severity": severity,
        "message": message,
        "target": row["target"],
    }


# --- Individual checks -------------------------------------------------------
# Each check takes a row (plus config) and returns a list of issues.

def check_placeholders(row, cfg):
    """Regression test 1: ICU/printf variables must match source exactly."""
    src, tgt = find_placeholders(row["source"]), find_placeholders(row["target"])
    if src != tgt:
        return [issue(row, "placeholder_mismatch", "Accuracy", "Major",
                      f"Source has {src}, target has {tgt}")]
    return []


def check_length(row, cfg):
    """Regression test 4: target must fit the UI character limit."""
    limit = int(row["max_chars"])
    length = len(row["target"])
    if length > limit:
        return [issue(row, "length_limit", "UX clarity", "Major",
                      f"{length} chars, limit is {limit} (+{length - limit})")]
    return []


def check_gendered(row, cfg):
    """Regression test 5: no masculine generics (inclusive language policy)."""
    terms = cfg["rules"]["gendered_terms"].get(row["locale"], [])
    found = [t for t in terms
             if re.search(rf"\b{t}\b", row["target"], re.IGNORECASE)]
    if found:
        return [issue(row, "gendered_language", "Cultural / dialectal appropriateness", "Major",
                      f"Masculine generic found: {', '.join(found)}")]
    return []


def check_untranslated(row, cfg):
    """Target identical to source (unless the term is on the allow list)."""
    if (row["source"].strip() == row["target"].strip()
            and row["source"].strip() not in cfg["rules"]["allow_identical"]):
        return [issue(row, "untranslated", "Accuracy", "Major",
                      "Target is identical to source")]
    return []


def check_glossary(row, cfg):
    """If the source contains a glossary term, the approved target must appear."""
    issues = []
    for entry in cfg["glossary"]:
        approved = entry.get(row["locale"], "")
        if (approved
                and re.search(rf"\b{re.escape(entry['en'])}\b", row["source"], re.IGNORECASE)
                # word boundary: "Configuració" must not match inside "Configuración"
                and not re.search(rf"\b{re.escape(approved)}\b", row["target"], re.IGNORECASE)):
            issues.append(issue(row, "glossary", "Terminology", "Minor",
                                f"'{entry['en']}' should be '{approved}'"))
    return issues


def check_inverted_punctuation(row, cfg):
    """ES only: questions and exclamations need opening ¿ / ¡."""
    if row["locale"] != "es-ES":
        return []
    tgt = row["target"]
    issues = []
    if "?" in tgt and "¿" not in tgt:
        issues.append(issue(row, "missing_inverted_mark", "Fluency", "Minor",
                            "Question without opening '¿'"))
    if "!" in tgt and "¡" not in tgt:
        issues.append(issue(row, "missing_inverted_mark", "Fluency", "Minor",
                            "Exclamation without opening '¡'"))
    return issues


def check_catalan(row, cfg):
    """CA only: punt volat (l·l), obsolete diacritics and Castilianisms."""
    if row["locale"] != "ca-ES":
        return []
    tgt = row["target"]
    issues = []
    # l.l or l•l or l-l instead of the correct middle dot (l·l)
    if re.search(r"l[.•\-]l", tgt, re.IGNORECASE):
        issues.append(issue(row, "punt_volat", "Fluency", "Minor",
                            "Wrong middle dot: use 'l·l'"))
    obsolete = [w for w in cfg["rules"].get("obsolete_diacritics_ca", [])
                if re.search(rf"\b{w}\b", tgt, re.IGNORECASE)]
    if obsolete:
        issues.append(issue(row, "obsolete_diacritic", "Fluency", "Minor",
                            f"Pre-2016 diacritic (IEC reform): {', '.join(obsolete)}"))
    found = [w for w in cfg["rules"]["castilianisms_ca"]
             if re.search(rf"\b{w}\b", tgt, re.IGNORECASE)]
    if found:
        issues.append(issue(row, "castilianism", "Cultural / dialectal appropriateness", "Major",
                            f"Castilianized form: {', '.join(found)}"))
    return issues


def check_whitespace(row, cfg):
    """Double spaces and leading/trailing whitespace."""
    tgt = row["target"]
    issues = []
    if "  " in tgt:
        issues.append(issue(row, "double_space", "Fluency", "Minor",
                            "Double space in target"))
    if tgt != tgt.strip():
        issues.append(issue(row, "edge_whitespace", "Fluency", "Minor",
                            "Leading or trailing whitespace"))
    return issues


CHECKS = [
    check_placeholders, check_length, check_gendered, check_untranslated,
    check_glossary, check_inverted_punctuation, check_catalan, check_whitespace,
]


# --- Runner ------------------------------------------------------------------

def load_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run(rows, cfg):
    issues = []
    for row in rows:
        for check in CHECKS:
            issues.extend(check(row, cfg))
    return issues


def main():
    parser = argparse.ArgumentParser(description="ES/CA LQA regression checks")
    parser.add_argument("--strings", default=str(HERE / "sample_strings.csv"))
    parser.add_argument("--glossary", default=str(HERE / "glossary.csv"))
    parser.add_argument("--rules", default=str(HERE / "rules.json"))
    parser.add_argument("--out", default=str(HERE / "qa_report.csv"))
    args = parser.parse_args()

    with open(args.rules, encoding="utf-8") as f:
        rules = json.load(f)
    cfg = {"rules": rules, "glossary": load_csv(args.glossary)}
    rows = load_csv(args.strings)

    issues = run(rows, cfg)

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        fields = ["id", "locale", "check", "mqm_category", "severity", "message", "target"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(issues)

    flagged = {i["id"] for i in issues}
    print(f"Strings checked: {len(rows)} | Issues: {len(issues)} | "
          f"Strings with issues: {len(flagged)}")
    for sev in ("Critical", "Major", "Minor"):
        print(f"  {sev:<8} {Counter(i['severity'] for i in issues)[sev]}")
    print("By check:")
    for check, n in Counter(i["check"] for i in issues).most_common():
        print(f"  {check:<22} {n}")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
