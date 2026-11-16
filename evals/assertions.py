"""
assertions.py - Custom Promptfoo assertions for ES/CA linguistic checks.

Why Python and not Promptfoo's built-in `regex`: built-in regexes run in
JavaScript, where \\b and \\w only know ASCII letters. A pattern such as
\\bvostè\\b does not match "vostè " there, because "è" is not a word character.
Python's `re` is Unicode-aware, so accented ES/CA words behave as expected.

Each function receives the model output and a context dict
(context["vars"] = test variables, context["config"] = assertion config)
and returns {"pass": bool, "score": 0 or 1, "reason": str}.

These are heuristics for known failure patterns, not a full language model.
"""

import json
import re
from pathlib import Path

# Shared with the string checker: one rules file, two tools.
RULES_PATH = Path(__file__).resolve().parent.parent / "lqa-checker" / "rules.json"
RULES = json.loads(RULES_PATH.read_text(encoding="utf-8"))

# Function words that exist in one language but not in the other.
SPANISH_ONLY = {
    "y", "con", "para", "puedes", "tienes", "algún", "alguna", "hasta", "pero",
    "muy", "más", "también", "hay", "cuando", "los", "las", "desde", "soporte",
    "ayuda", "días", "hábiles", "usted",
}
CATALAN_ONLY = {
    "i", "amb", "per", "pots", "tens", "fins", "però", "molt", "més", "també",
    "quan", "els", "dies", "feiners", "aquest", "aquesta", "teu", "teva",
}
ENGLISH_ONLY = {"the", "you", "your", "please", "with", "and"}

FORMAL_PATTERNS = {
    "es-ES": [
        r"\busted(es)?\b",
        r"\bsus?\s+(cuenta|perfil|plan|suscripción|espacio|área|pago|reembolso|datos)\b",
    ],
    "ca-ES": [
        r"\bvostès?\b",
        r"\b(el seu|la seva|els seus|les seves)\s+"
        r"(compte|perfil|pla|subscripció|espai|pagament|reemborsament|dades)\b",
    ],
}

# "5-7 dies", "5 a 7 días", "entre 5 y 10 días", "5 i 10 dies", "14 días"
DAY_FIGURE_RE = re.compile(r"(\d+)(?:\s?(?:-|–|a|y|e|i|o)\s?(\d+))?\s+(?:días|dies)")


def _result(passed, reason):
    return {"pass": passed, "score": 1 if passed else 0, "reason": reason}


def _words(text):
    """Lowercase words, Unicode-aware (keeps à, é, ï, ç, ñ, l·l parts)."""
    return set(re.findall(r"[^\W\d_]+", text.lower()))


def language_matches_locale(output, context):
    """The reply must stay in the user's language (defect D-021)."""
    locale = context["vars"]["locale"]
    limit = (context.get("config") or {}).get("max_foreign_markers", 1)
    words = _words(output)

    if locale == "ca-ES":
        # Known Castilianisms (including Spanish menu names such as "Ajustes")
        # are never valid Catalan: one is enough to fail.
        castilianisms = sorted(words & set(RULES["castilianisms_ca"]))
        if castilianisms:
            return _result(False, f"Castilianism in a ca-ES reply: {', '.join(castilianisms)}")
        foreign = SPANISH_ONLY | ENGLISH_ONLY
    else:
        # Catalan menu names in a Spanish reply point to a non-existent UI path.
        ca_ui = sorted(words & set(RULES["catalan_ui_terms_in_es"]))
        if ca_ui:
            return _result(False, f"Catalan UI term in an es-ES reply: {', '.join(ca_ui)}")
        foreign = CATALAN_ONLY | ENGLISH_ONLY
    found = sorted(words & foreign)

    # Function words can be ambiguous (e.g. CA "para" = "it stops"), so a single
    # hit is tolerated by default.
    if len(found) > limit:
        return _result(False, f"Language switch in a {locale} reply: {', '.join(found)}")
    return _result(True, f"Reply stays in {locale}")


def informal_register(output, context):
    """The product addresses the user as tú / tu (defects D-017, D-026)."""
    locale = context["vars"]["locale"]
    found = [m.group(0) for pattern in FORMAL_PATTERNS.get(locale, [])
             for m in re.finditer(pattern, output, re.IGNORECASE)]
    if found:
        return _result(False, f"Formal register: {', '.join(found)}")
    return _result(True, "Informal register")


def no_gendered_generics(output, context):
    """No masculine generics such as Bienvenido / Benvingut (D-003, D-019)."""
    locale = context["vars"]["locale"]
    # Narrower list than the UI-string checker: in free text "registrado" can
    # agree with a noun ("el correo registrado"), so only terms that address
    # the user are checked here.
    terms = RULES["gendered_address_terms"].get(locale, [])
    found = [t for t in terms if re.search(rf"\b{t}\b", output, re.IGNORECASE)]
    if found:
        return _result(False, f"Masculine generic: {', '.join(found)}")
    return _result(True, "No masculine generics")


def day_figures_match_policy(output, context):
    """Every 'N days' figure in the reply must be one the policy allows (D-005)."""
    allowed = set((context.get("config") or {}).get("allowed_days", []))
    figures = set()
    for match in DAY_FIGURE_RE.finditer(output.lower()):
        figures.update(int(n) for n in match.groups() if n)
    wrong = sorted(figures - allowed)
    if wrong:
        return _result(False, f"Day figures not in policy: {wrong} (allowed: {sorted(allowed)})")
    return _result(True, "All day figures match the policy")


def catalan_orthography(output, context):
    """CA only: diacritic accents removed by the 2016 IEC spelling reform (e.g. vés -> ves)."""
    if context["vars"]["locale"] != "ca-ES":
        return _result(True, "Not a Catalan reply")
    found = sorted(_words(output) & set(RULES["obsolete_diacritics_ca"]))
    if found:
        return _result(False, f"Pre-2016 diacritic accent (IEC 2016 reform): {', '.join(found)}")
    return _result(True, "No obsolete diacritics")
