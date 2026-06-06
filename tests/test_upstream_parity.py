"""Drift-Guard: lohnsteuer_bmf muss bitgenau wie rechner-hub-api/steuerlogik rechnen.

Dieses Paket ist ein Carve-out aus rechner-hub-api/steuerlogik. Die SSoT bleibt
dort; hier wurde nur die Datenschicht (SQLite -> _data.py) getauscht. Solange
beide identisch rechnen, ist der Carve-out sauber.

Wird ÜBERSPRUNGEN, wenn das Upstream-Paket nicht importierbar ist (z.B. in der
öffentlichen GitHub-CI, die rechner-hub-api nicht auscheckt). Lokal — mit dem
Sibling-Repo rechner-hub-api neben diesem — läuft der Vergleich scharf.
"""

import sys
from pathlib import Path

import pytest


def _try_import_upstream():
    try:
        import steuerlogik  # noqa: F401
    except ImportError:
        sibling = Path(__file__).resolve().parents[2] / "rechner-hub-api"
        if sibling.is_dir():
            sys.path.insert(0, str(sibling))
    try:
        from steuerlogik import einkommensteuer as up_est
        from steuerlogik import einkommensteuer_tarif as up_tarif
        from steuerlogik import lohnsteuer_pap as up_lp
    except ImportError:
        return None
    return up_est, up_tarif, up_lp


_UPSTREAM = _try_import_upstream()

pytestmark = pytest.mark.skipif(
    _UPSTREAM is None,
    reason="Upstream rechner-hub-api/steuerlogik nicht verfügbar — Parity-Check übersprungen.",
)


JAHRE = (2024, 2025, 2026)
ZVE_WERTE = (0, 12348, 15000, 30000, 50000, 70000, 100000, 277825, 300000)


@pytest.mark.parametrize("jahr", JAHRE)
@pytest.mark.parametrize("zve", ZVE_WERTE)
def test_parity_einkommensteuer(zve: int, jahr: int) -> None:
    from lohnsteuer_bmf import einkommensteuer, einkommensteuer_splitting

    up_est = _UPSTREAM[0]
    assert einkommensteuer(zve, jahr) == up_est.einkommensteuer(zve, jahr)
    assert einkommensteuer_splitting(zve, jahr) == up_est.einkommensteuer_splitting(zve, jahr)


@pytest.mark.parametrize("jahr", JAHRE)
@pytest.mark.parametrize("est", (0.0, 20000.0, 30864.0, 105550.0))
@pytest.mark.parametrize("zusammen", (True, False))
def test_parity_soli(est: float, zusammen: bool, jahr: int) -> None:
    from lohnsteuer_bmf import solidaritaetszuschlag

    up_est = _UPSTREAM[0]
    assert solidaritaetszuschlag(est, zusammen, jahr) == up_est.solidaritaetszuschlag(
        est, zusammen, jahr
    )


def test_parity_kirchensteuer() -> None:
    from lohnsteuer_bmf import BUNDESLAENDER, kirchensteuer

    up_est = _UPSTREAM[0]
    for bl in BUNDESLAENDER:
        assert kirchensteuer(30864, bl) == up_est.kirchensteuer(30864, bl)


@pytest.mark.parametrize("jahr", JAHRE)
@pytest.mark.parametrize("zve", ZVE_WERTE)
@pytest.mark.parametrize("zusammen", (True, False))
def test_parity_tarif_endpoint(zve: int, zusammen: bool, jahr: int) -> None:
    from lohnsteuer_bmf import berechne_einkommensteuer_tarif

    up_tarif = _UPSTREAM[1]
    a = berechne_einkommensteuer_tarif(zve, zusammenveranlagung=zusammen, jahr=jahr)
    b = up_tarif.berechne_einkommensteuer_tarif(zve, zusammenveranlagung=zusammen, jahr=jahr)
    assert a == b


_LST_FAELLE = [
    (60000.0, 1, "Nordrhein-Westfalen", False, 0, 1990, False),
    (60000.0, 2, "Nordrhein-Westfalen", False, 1, 1990, False),
    (60000.0, 3, "Nordrhein-Westfalen", True, 0, 1990, False),
    (60000.0, 4, "Bayern", True, 2, 1985, False),
    (60000.0, 5, "Nordrhein-Westfalen", False, 0, 1990, False),
    (60000.0, 6, "Nordrhein-Westfalen", False, 0, 1990, False),
    (24000.0, 1, "Sachsen", False, 0, 2000, True),
    (96000.0, 1, "Nordrhein-Westfalen", False, 0, 1970, False),
    (150000.0, 5, "Hamburg", True, 3, 1980, False),
]


@pytest.mark.parametrize("jahr", JAHRE)
@pytest.mark.parametrize("brutto,sk,bl,kist,kinder,gj,sachsen", _LST_FAELLE)
def test_parity_lohnsteuer_pap(
    brutto: float,
    sk: int,
    bl: str,
    kist: bool,
    kinder: int,
    gj: int,
    sachsen: bool,
    jahr: int,
) -> None:
    from lohnsteuer_bmf import berechne_lohnsteuer_pap

    up_lp = _UPSTREAM[2]
    kw = dict(
        brutto_jahr=brutto,
        steuerklasse=sk,
        bundesland=bl,
        mit_kirchensteuer=kist,
        kinder=kinder,
        geburtsjahr=gj,
        kv_zusatzbeitrag=2.9,
        ist_sachsen=sachsen,
        jahr=jahr,
    )
    assert berechne_lohnsteuer_pap(**kw) == up_lp.berechne_lohnsteuer_pap(**kw)
