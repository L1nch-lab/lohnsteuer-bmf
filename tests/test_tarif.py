"""Tests für lohnsteuer_bmf.tarif (ESt-Tarif-Endpoint)."""

import pytest

from lohnsteuer_bmf import berechne_einkommensteuer_tarif


def test_minimal() -> None:
    r = berechne_einkommensteuer_tarif(50000, jahr=2026)
    assert r["einkommensteuer"] > 0
    assert r["grenzsteuersatz"] > 0
    assert r["durchschnittssteuersatz"] > 0


def test_grundfreibetrag_steuerfrei() -> None:
    r = berechne_einkommensteuer_tarif(12000, jahr=2026)
    assert r["einkommensteuer"] == 0.0
    assert r["grenzsteuersatz"] == 0.0
    assert r["tarifzone"]["zone"] == 1
    assert r["tarifzone"]["name"] == "Grundfreibetrag"


def test_zone3_grenzsteuersatz() -> None:
    r = berechne_einkommensteuer_tarif(50000, jahr=2026)
    assert r["tarifzone"]["zone"] == 3
    assert 24 <= r["grenzsteuersatz"] <= 42


def test_splitting_guenstiger() -> None:
    einzel = berechne_einkommensteuer_tarif(80000, zusammenveranlagung=False)
    split = berechne_einkommensteuer_tarif(80000, zusammenveranlagung=True)
    assert split["einkommensteuer"] < einzel["einkommensteuer"]


def test_splitting_grundfreibetrag_verdoppelt() -> None:
    r = berechne_einkommensteuer_tarif(50000, zusammenveranlagung=True, jahr=2026)
    assert r["grundfreibetrag"] == 12348 * 2


def test_kirchensteuer_erhoeht_gesamt() -> None:
    ohne = berechne_einkommensteuer_tarif(50000, kirchensteuer=False)
    mit = berechne_einkommensteuer_tarif(50000, kirchensteuer=True, bundesland="Bayern")
    assert mit["kirchensteuer"] > 0
    assert mit["steuer_gesamt"] > ohne["steuer_gesamt"]


def test_reichensteuer_zone5() -> None:
    r = berechne_einkommensteuer_tarif(300000, jahr=2026)
    assert r["tarifzone"]["zone"] == 5
    assert r["grenzsteuersatz"] == pytest.approx(45.0, abs=0.5)


def test_zve_null_kein_durchschnittssteuersatz() -> None:
    """zvE = 0: Durchschnittssteuersatz + Belastungsquote = 0.0 (Division-durch-Null-Schutz)."""
    r = berechne_einkommensteuer_tarif(0, jahr=2026)
    assert r["einkommensteuer"] == 0.0
    assert r["durchschnittssteuersatz"] == 0.0
    assert r["belastungsquote"] == 0.0


def test_envelope_keys() -> None:
    r = berechne_einkommensteuer_tarif(50000)
    assert {
        "zve",
        "einkommensteuer",
        "solidaritaetszuschlag",
        "kirchensteuer",
        "steuer_gesamt",
        "grenzsteuersatz",
        "durchschnittssteuersatz",
        "belastungsquote",
        "tarifzone",
        "grundfreibetrag",
        "zusammenveranlagung",
        "steuerjahr",
    } <= set(r)
