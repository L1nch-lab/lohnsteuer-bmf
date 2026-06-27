"""Tests für lohnsteuer_bmf.einkommensteuer (§32a EStG, Soli, KiSt)."""

import json
from pathlib import Path

import pytest

from lohnsteuer_bmf import (
    BUNDESLAENDER,
    UNTERSTUETZTE_JAHRE,
    einkommensteuer,
    einkommensteuer_splitting,
    kirchensteuer,
    solidaritaetszuschlag,
)

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden(filename: str) -> list[dict]:
    return json.loads((GOLDEN_DIR / filename).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Golden-/Regressionswerte (2026 primärquellen-verankert; 2024/2025 == Upstream,
# siehe Datenintegritäts-Vermerk in _data.py)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", load_golden("einkommensteuer.json"))
def test_einkommensteuer_golden(case: dict) -> None:
    est = einkommensteuer(case["zve"], case["jahr"])
    assert est == case["est"], (
        f"zve={case['zve']}, jahr={case['jahr']}: erwartet {case['est']}, erhalten {est}"
    )
    soli = solidaritaetszuschlag(float(est), jahr=case["jahr"])
    assert abs(soli - case["soli"]) < 0.02, f"Soli: erwartet {case['soli']}, erhalten {soli}"


@pytest.mark.parametrize(
    "zve,jahr",
    [(0, 2024), (11604, 2024), (0, 2025), (12096, 2025), (0, 2026), (12348, 2026)],
)
def test_grundfreibetrag_steuerfrei(zve: int, jahr: int) -> None:
    assert einkommensteuer(zve, jahr) == 0


def test_unbekanntes_jahr() -> None:
    with pytest.raises(ValueError, match="2099"):
        einkommensteuer(50000, 2099)


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------


def test_splitting_guenstiger_als_einzel() -> None:
    einzel = einkommensteuer(80000, 2026)
    split = einkommensteuer_splitting(80000, 2026)
    assert split < einzel


def test_splitting_ist_doppelte_haelfte() -> None:
    assert einkommensteuer_splitting(60000, 2026) == einkommensteuer(30000, 2026) * 2


# ---------------------------------------------------------------------------
# Solidaritätszuschlag — Freigrenze + Milderungszone
# ---------------------------------------------------------------------------


def test_soli_unter_freigrenze_null() -> None:
    # 2026 Einzel-Freigrenze 20.350 EUR ESt
    assert solidaritaetszuschlag(20000, jahr=2026) == 0.0


def test_soli_voll_5komma5_prozent() -> None:
    # Deutlich über Milderungszone -> volle 5,5 %
    est = 200000.0
    assert solidaritaetszuschlag(est, jahr=2026) == pytest.approx(est * 0.055, abs=0.01)


def test_soli_unbekanntes_jahr() -> None:
    """Nicht unterstütztes Steuerjahr → ValueError mit Jahresangabe."""
    with pytest.raises(ValueError, match="9999"):
        solidaritaetszuschlag(50000.0, jahr=9999)


def test_get_steuerjahr_parameter_unbekanntes_jahr() -> None:
    """Datenschicht: unbekanntes Steuerjahr → KeyError."""
    from lohnsteuer_bmf._data import get_steuerjahr_parameter

    with pytest.raises(KeyError, match="9999"):
        get_steuerjahr_parameter(9999)


# ---------------------------------------------------------------------------
# Kirchensteuer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bundesland", ["Bayern", "Baden-Württemberg"])
def test_kirchensteuer_8_prozent(bundesland: str) -> None:
    assert kirchensteuer(10000, bundesland) == pytest.approx(800.0)


@pytest.mark.parametrize("bundesland", ["Berlin", "Nordrhein-Westfalen", "Sachsen"])
def test_kirchensteuer_9_prozent(bundesland: str) -> None:
    assert kirchensteuer(10000, bundesland) == pytest.approx(900.0)


def test_kirchensteuer_unbekanntes_bundesland() -> None:
    with pytest.raises(ValueError, match="Unbekanntes Bundesland"):
        kirchensteuer(10000, "Tirol")


def test_alle_16_bundeslaender_bekannt() -> None:
    assert len(BUNDESLAENDER) == 16
    for bl in BUNDESLAENDER:
        assert kirchensteuer(10000, bl) in (800.0, 900.0)


def test_unterstuetzte_jahre() -> None:
    assert UNTERSTUETZTE_JAHRE == (2024, 2025, 2026)
