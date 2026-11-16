"""Unit tests for the custom assertions. Run: python test_assertions.py (or pytest)."""

from assertions import (catalan_orthography, day_figures_match_policy,
                        informal_register, language_matches_locale,
                        no_gendered_generics)
from judge import partial_refund_judge


def ctx(locale, **config):
    return {"vars": {"locale": locale}, "config": config}


def test_catalan_reply_switching_to_spanish_fails():
    reply = "Ves a Configuració > Idioma. Si tienes algún problema, contacta con soporte."
    assert not language_matches_locale(reply, ctx("ca-ES"))["pass"]


def test_clean_catalan_reply_passes():
    reply = "Ves a Configuració > Idioma. Si tens cap problema, contacta amb el servei d'assistència."
    assert language_matches_locale(reply, ctx("ca-ES"))["pass"]


def test_single_castilianism_fails():
    assert not language_matches_locale("Ves a Configuración > Idioma.", ctx("ca-ES"))["pass"]


def test_spanish_menu_path_in_catalan_reply_fails():
    # Real Gemini 3.5 Flash-Lite output, EC-012 (November 2026 run)
    reply = "Hola! El segon pas és completar el teu perfil (Ajustes > Perfil)."
    assert not language_matches_locale(reply, ctx("ca-ES"))["pass"]


def test_reembolsar_castilianism_fails():
    # Real Nemotron 3 Ultra output, EC-006 (November 2026 OpenRouter run). Catalan: "reemborsar".
    reply = "No, els mesos parcials no es reembolsen. Mantindràs l'accés fins al final del període."
    assert not language_matches_locale(reply, ctx("ca-ES"))["pass"]
    assert language_matches_locale(reply.replace("reembolsen", "reemborsen"), ctx("ca-ES"))["pass"]


def test_catalan_menu_path_in_spanish_reply_fails():
    reply = "Puedes cambiar tu plan en Configuració > Subscripció."
    assert not language_matches_locale(reply, ctx("es-ES"))["pass"]


def test_spanish_reply_switching_to_catalan_fails():
    reply = "Puedes cambiarlo en Ajustes. Si tens cap problema, contacta amb nosaltres."
    assert not language_matches_locale(reply, ctx("es-ES"))["pass"]


def test_formal_register():
    assert not informal_register("Configure su perfil.", ctx("es-ES"))["pass"]
    assert not informal_register("Pot vostè canviar-ho a Configuració.", ctx("ca-ES"))["pass"]
    assert informal_register("Completa tu perfil.", ctx("es-ES"))["pass"]
    assert informal_register("Completa el teu perfil.", ctx("ca-ES"))["pass"]


def test_gendered_greeting():
    assert not no_gendered_generics("¡Bienvenido a NovaChat!", ctx("es-ES"))["pass"]
    assert not no_gendered_generics("Benvingut a NovaChat!", ctx("ca-ES"))["pass"]
    assert no_gendered_generics("¡Hola! Usa el correo registrado.", ctx("es-ES"))["pass"]


def test_day_figures():
    allowed = ctx("es-ES", allowed_days=[14])
    assert not day_figures_match_policy("en 5-7 dies feiners", allowed)["pass"]
    assert not day_figures_match_policy("de 5 a 7 días hábiles", allowed)["pass"]
    assert day_figures_match_policy("hasta 14 días hábiles", allowed)["pass"]
    # Real Gemini output (baseline run): "y" as connector was missed at first
    result = day_figures_match_policy("entre 5 y 10 días laborables", allowed)
    assert not result["pass"] and "5" in result["reason"]


def test_refund_timeframe_accepts_narrow_no_break_spaces():
    import json
    import re
    from pathlib import Path
    cases = [json.loads(line) for line in
             (Path(__file__).parent / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    case = next(c for c in cases if c["vars"]["case_id"] == "EC-003")
    pattern = next(a["value"] for a in case["assert"] if a["type"] == "regex")
    assert re.search(pattern, "Hasta 14\u202fdías\u202fhábiles.")
    assert not re.search(pattern, "Hasta 7\u202fdías\u202fhábiles.")


def test_obsolete_diacritic():
    # Real Gemini output (grounded run, EC-007)
    assert not catalan_orthography("Per canviar l'idioma, vés a Configuració > Idioma.", ctx("ca-ES"))["pass"]
    assert catalan_orthography("Per canviar l'idioma, ves a Configuració > Idioma.", ctx("ca-ES"))["pass"]
    assert catalan_orthography("Vés", ctx("es-ES"))["pass"]



def test_judge_replays_cached_verdicts_offline():
    # Both answers are in recorded/judge_verdicts.json, so no API call is made.
    trap = ("No te preocupes: te devolveremos la parte proporcional del mes. "
            "Mantienes el acceso hasta el final del periodo de facturación.")
    assert not partial_refund_judge(trap, ctx("es-ES"))["pass"]
    good = ("Lo siento, pero no: el mes que ya has empezado no se devuelve. "
            "Eso sí, podrás seguir usando Pro hasta la fecha de renovación.")
    assert partial_refund_judge(good, ctx("es-ES"))["pass"]


def test_judge_without_cached_verdict_fails_loudly():
    import os
    os.environ.pop("JUDGE_LIVE", None)
    result = partial_refund_judge("Una respuesta que el juez no ha visto nunca.", ctx("es-ES"))
    assert not result["pass"] and "No cached verdict" in result["reason"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
