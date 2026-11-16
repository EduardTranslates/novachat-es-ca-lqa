"""Minimal tests: run with `python -m pytest` (or `python test_lqa_checks.py`)."""

from lqa_checks import (check_placeholders, check_catalan,
                        check_inverted_punctuation, check_gendered)

CFG = {
    "rules": {
        "gendered_terms": {"es-ES": ["bienvenido"], "ca-ES": ["benvingut"]},
        "castilianisms_ca": ["configuración"],
        "obsolete_diacritics_ca": ["vés"],
        "allow_identical": [],
    },
    "glossary": [],
}


def row(target, source="x", locale="es-ES"):
    return {"id": "T", "locale": locale, "source": source,
            "target": target, "max_chars": "100"}


def test_placeholder_typo_is_caught():
    assert check_placeholders(row("Tienes {cuont}", "You have {count}"), CFG)


def test_placeholder_ok_passes():
    assert not check_placeholders(row("Tienes {count}", "You have {count}"), CFG)


def test_punt_volat():
    assert check_catalan(row("intel.ligència", locale="ca-ES"), CFG)
    assert not check_catalan(row("intel·ligència", locale="ca-ES"), CFG)


def test_obsolete_diacritic():
    issues = check_catalan(row("Vés a Configuració", locale="ca-ES"), CFG)
    assert [i for i in issues if i["check"] == "obsolete_diacritic"]
    assert not check_catalan(row("Ves a Configuració", locale="ca-ES"), CFG)


def test_inverted_question_mark():
    assert check_inverted_punctuation(row("Quieres salir?"), CFG)
    assert not check_inverted_punctuation(row("¿Quieres salir?"), CFG)


def test_gendered_greeting():
    assert check_gendered(row("¡Bienvenido, {name}!"), CFG)
    assert not check_gendered(row("¡Hola de nuevo, {name}!"), CFG)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
