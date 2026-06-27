"""Tests für lohnsteuer_bmf.lohnsteuer (BMF-PAP 2026)."""

import json
from pathlib import Path

import pytest

from lohnsteuer_bmf import berechne_lohnsteuer_pap, berechne_zve

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden(filename: str) -> list[dict]:
    return json.loads((GOLDEN_DIR / filename).read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", load_golden("lohnsteuer.json"))
def test_lohnsteuer_golden_2026(case: dict) -> None:
    """2026-Regressionswerte (Eingaben primärquellen-verifiziert)."""
    erwartet = case.pop("erwartet")
    result = berechne_lohnsteuer_pap(
        brutto_jahr=case["brutto_jahr"],
        steuerklasse=case["steuerklasse"],
        bundesland=case["bundesland"],
        mit_kirchensteuer=case["mit_kirchensteuer"],
        kinder=case["kinder"],
        geburtsjahr=case["geburtsjahr"],
        kv_zusatzbeitrag=case["kv_zusatzbeitrag"],
        ist_sachsen=case["ist_sachsen"],
        jahr=case["jahr"],
    )
    for key, val in erwartet.items():
        assert result[key] == pytest.approx(val, abs=0.01), (
            f"{key}: erwartet {val}, erhalten {result[key]}"
        )


def _lst(brutto: float, sk: int, **kw: object) -> float:
    defaults: dict = dict(
        bundesland="Nordrhein-Westfalen",
        mit_kirchensteuer=False,
        kinder=0,
        geburtsjahr=1990,
        kv_zusatzbeitrag=2.9,
        ist_sachsen=False,
        jahr=2026,
    )
    defaults.update(kw)
    return berechne_lohnsteuer_pap(brutto_jahr=brutto, steuerklasse=sk, **defaults)[
        "lohnsteuer_monat"
    ]


def test_headline_stkl1_5000_2026() -> None:
    """Top-Query: Steuerklasse 1, 5.000 €/Monat, 2026."""
    assert _lst(60000.0, 1) == pytest.approx(777.33, abs=0.01)


def test_steuerklassen_ordnung() -> None:
    """SK3 < SK1 < SK5; SK6 hoch (kein ANP/SAP)."""
    sk1 = _lst(60000.0, 1)
    sk3 = _lst(60000.0, 3)
    sk5 = _lst(60000.0, 5)
    assert sk3 < sk1 < sk5


def test_kirchensteuer_wird_ausgewiesen() -> None:
    mit = berechne_lohnsteuer_pap(
        brutto_jahr=60000.0,
        steuerklasse=1,
        bundesland="Bayern",
        mit_kirchensteuer=True,
        kinder=0,
        geburtsjahr=1990,
        kv_zusatzbeitrag=2.9,
        ist_sachsen=False,
        jahr=2026,
    )
    assert mit["kirchensteuer_monat"] > 0


def test_niedriges_brutto_keine_lohnsteuer() -> None:
    assert _lst(12000.0, 1) == 0.0


def test_berechne_zve_nichtnegativ() -> None:
    assert berechne_zve(5000.0, steuerklasse=1) >= 0.0


def test_zve_im_ergebnis() -> None:
    r = berechne_lohnsteuer_pap(
        brutto_jahr=60000.0,
        steuerklasse=1,
        bundesland="Nordrhein-Westfalen",
        mit_kirchensteuer=False,
        kinder=0,
        geburtsjahr=1990,
        kv_zusatzbeitrag=2.9,
        ist_sachsen=False,
        jahr=2026,
    )
    assert set(r) == {
        "lohnsteuer_monat",
        "soli_monat",
        "kirchensteuer_monat",
        "zve_jahr",
        "vorsorgepauschale",
    }


# --- berechne_zve: Steuerklassen-Sonderpfade (ANP/SAP-Abzug) ---


def test_berechne_zve_sk6_kein_anp_sap() -> None:
    """SK6 (zweites Dienstverhältnis): kein ANP/SAP → höheres zvE als SK1."""
    assert berechne_zve(60000.0, steuerklasse=6) > berechne_zve(60000.0, steuerklasse=1)


def test_berechne_zve_sk3_doppelter_sap() -> None:
    """SK3 (Splitting): doppelter SAP → niedrigeres zvE als SK1."""
    assert berechne_zve(60000.0, steuerklasse=3) < berechne_zve(60000.0, steuerklasse=1)


# --- MST5_6: alle Stufen der Steuerklasse V/VI (Differenzmethode) ---


def test_sk5_zve_null_keine_steuer() -> None:
    """SK5, sehr niedriges Brutto → zvE=0 → MST5_6 gibt 0 zurück."""
    r = berechne_lohnsteuer_pap(
        brutto_jahr=1000.0,
        steuerklasse=5,
        bundesland="Nordrhein-Westfalen",
        mit_kirchensteuer=False,
        kinder=0,
        geburtsjahr=1990,
        kv_zusatzbeitrag=2.9,
        ist_sachsen=False,
        jahr=2026,
    )
    assert r["zve_jahr"] == 0.0
    assert r["lohnsteuer_monat"] == 0.0


def test_sk5_unter_w1() -> None:
    """SK5, zvE ≤ W1 (14.071 €): unterste MST5_6-Zone, positive Steuer."""
    assert _lst(18000.0, 5) > 0.0


def test_sk5_zwischen_w1_und_w2() -> None:
    """SK5, W1 < zvE ≤ W2 (34.939 €): Vergleichsberechnung greift, monoton steigend."""
    assert _lst(45000.0, 5) > _lst(18000.0, 5)


def test_sk5_reichensteuer_stufe() -> None:
    """SK5, zvE > W3 (222.260 €): Spitzen- + Reichensteuer-Stufe (42 % / 45 %)."""
    assert _lst(300000.0, 5) > _lst(60000.0, 5)


# --- PV-Beitragssatz: alle drei Kinder-Pfade (Kinderlos-Zuschlag / Basis / Abschlag) ---


def test_pv_satz_ein_kind_basis() -> None:
    """1 Kind → PV-Basissatz (kein Kinderlos-Zuschlag, kein Mehrkind-Abschlag).

    Lohnsteuer ist strikt monoton in der Kinderzahl: 0 Kinder < 1 Kind < 2 Kinder
    (weniger PV-Abzug in der Vorsorgepauschale → höheres zvE → höhere Steuer).
    """
    assert _lst(60000.0, 1, kinder=0) < _lst(60000.0, 1, kinder=1) < _lst(60000.0, 1, kinder=2)
