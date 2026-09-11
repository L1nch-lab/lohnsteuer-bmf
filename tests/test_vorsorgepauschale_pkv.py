"""Vorsorgepauschale für privat Krankenversicherte + Höchstbetragszweig MVSPHB.

Deckt die beiden PAP-Module ab, die bis 2026.2 fehlten:

    MVSPKVPV (Anlage 1 S. 27)  PKV-Zweig, § 39b Abs. 2 S. 5 Nr. 3 Buchst. d EStG
    MVSPHB   (Anlage 1 S. 28)  ALV-Höchstbetrag, Buchst. e

MVSPHB läuft nur bei ALV != 1 UND STKL != 6 (Aufrufbedingung in UPEVP, S. 26).
Der Normtext bestätigt das unabhängig: Buchst. e gilt "in den Steuerklassen
I bis V".

Dieselbe Systematik erklärt die Asymmetrie in MVSPKVPV:

    Buchst. b, c (GKV)  "in den Steuerklassen I bis VI"  -> kein STKL-Check
    Buchst. d    (PKV)  "in den Steuerklassen I bis V"   -> STKL 6 => 0

Die Unit-Tests sind aus rechner-hub-api übernommen. Die End-to-End-Werte am
Ende stammen aus der offiziellen BMF-Schnittstelle (LSt2026ext, Abfrage vom
11.09.2026), nicht aus dieser Implementierung.
"""

import pytest

from lohnsteuer_bmf import berechne_lohnsteuer_pap
from lohnsteuer_bmf.konstanten import AV_AN
from lohnsteuer_bmf.lohnsteuer import (
    _BBGKV_JAHR,
    _BBGRV_JAHR,
    _VSPHB_MAX,
    _berechne_vorsorgepauschale,
)

# 60.000 EUR/Jahr: hoch genug für vollen Grenzsteuersatz, niedrig genug, dass
# ein günstiger PKV-Tarif ein kleines VSPKVPV ergibt. Genau in diesem Band
# bindet MVSPHB bei PKV.
BRUTTO = 60_000.0
VSPR = min(BRUTTO, _BBGRV_JAHR) * 9.3 / 100


def vsp(**kw: object) -> float:
    """Aufruf mit den Standardwerten der Testfälle."""
    args: dict = {
        "brutto_jahr": BRUTTO,
        "kv_zusatzbeitrag": 2.9,
        "kinder": 0,
        "geburtsjahr": 1985,
        "ist_sachsen": False,
    }
    args.update(kw)
    return _berechne_vorsorgepauschale(**args)


class TestPkvZweig:
    def test_beitrag_minus_zuschuss_wird_angesetzt(self) -> None:
        """VSPKVPV = (PKPV - PKPVAGZ) * 12, beides Cent-Monatsbeträge."""
        ergebnis = vsp(
            steuerklasse=1,
            pkv=True,
            pkpv_monat_cent=80_000,  # 800 EUR
            pkpvagz_monat_cent=40_000,  # 400 EUR
            alv_pflichtversichert=False,  # MVSPHB aus, damit nur der PKV-Teil wirkt
        )
        assert ergebnis == pytest.approx(VSPR + (800 - 400) * 12, abs=0.01)

    def test_zuschuss_groesser_als_beitrag_wird_nicht_negativ(self) -> None:
        """Der PAP klemmt VSPKVPV bei 0, sonst erhöhte ein Zuschuss das zvE."""
        ergebnis = vsp(
            steuerklasse=1,
            pkv=True,
            pkpv_monat_cent=20_000,
            pkpvagz_monat_cent=40_000,
            alv_pflichtversichert=False,
        )
        assert ergebnis == pytest.approx(VSPR, abs=0.01)

    def test_steuerklasse_6_setzt_kv_teil_auf_null(self) -> None:
        """Buchst. d gilt nur in den Steuerklassen I bis V."""
        ergebnis = vsp(steuerklasse=6, pkv=True, pkpv_monat_cent=80_000, pkpvagz_monat_cent=0)
        assert ergebnis == pytest.approx(VSPR, abs=0.01)

    def test_gkv_kennt_keinen_steuerklassen_check(self) -> None:
        """Gegenstück: Buchst. b/c gelten in I bis VI.

        Nur MVSPHB fällt bei StKl 6 weg, deshalb hier mit ALV=1 verglichen,
        sonst misst man den Höchstbetragszweig mit.
        """
        stkl1 = vsp(steuerklasse=1, alv_pflichtversichert=False)
        stkl6 = vsp(steuerklasse=6, alv_pflichtversichert=False)
        assert stkl1 == pytest.approx(stkl6, abs=0.01)


class TestRentenversicherungsMerker:
    def test_krv_1_streicht_den_rv_teilbetrag(self) -> None:
        """KRV = 1: VSPR = 0 (UPEVP, S. 26; § 39b Abs. 2 S. 5 Nr. 3 Buchst. a EStG)."""
        mit_rv = vsp(steuerklasse=1, alv_pflichtversichert=False)
        ohne_rv = vsp(steuerklasse=1, alv_pflichtversichert=False, rv_pflichtversichert=False)
        assert mit_rv - ohne_rv == pytest.approx(VSPR, abs=0.01)


class TestMvsphbAufrufbedingung:
    def test_greift_bei_alv_pflicht_und_stkl_ungleich_6(self) -> None:
        basis = dict(steuerklasse=1, pkv=True, pkpv_monat_cent=25_000, pkpvagz_monat_cent=12_500)
        mit = vsp(**basis, alv_pflichtversichert=True)
        ohne = vsp(**basis, alv_pflichtversichert=False)
        # Überschlag aus dem Plan: bei kleinem Netto-Beitrag rund +400 EUR
        assert mit - ohne == pytest.approx(400.0, abs=1.0)

    def test_greift_nicht_in_steuerklasse_6(self) -> None:
        """StKl 6 schließt das Gate selbst, ALV ist dann irrelevant."""
        basis = dict(steuerklasse=6, pkv=True, pkpv_monat_cent=25_000, pkpvagz_monat_cent=12_500)
        offen = vsp(**basis, alv_pflichtversichert=True)
        zu = vsp(**basis, alv_pflichtversichert=False)
        assert offen == pytest.approx(zu, abs=0.01)


class TestMvsphbRechnung:
    def test_deckel_1900_greift(self) -> None:
        """VSPALV + VSPKVPV wird bei 1.900 EUR gekappt (Buchst. e)."""
        ergebnis = vsp(
            steuerklasse=1,
            pkv=True,
            pkpv_monat_cent=25_000,
            pkpvagz_monat_cent=12_500,
            alv_pflichtversichert=True,
        )
        # VSPALV (780) + VSPKVPV (1500) = 2280 > 1900 -> gekappt
        assert ergebnis == pytest.approx(VSPR + _VSPHB_MAX, abs=0.01)

    def test_nimmt_den_groesseren_der_beiden_wege(self) -> None:
        """VSP = max(VSP, VSPN): bei teurem Tarif bleibt der Normalweg vorn."""
        teuer = vsp(
            steuerklasse=1,
            pkv=True,
            pkpv_monat_cent=80_000,
            pkpvagz_monat_cent=40_000,
            alv_pflichtversichert=True,
        )
        # VSPKVPV = 4800 -> VSPN wäre VSPR + 1900, der Normalweg VSPR + 4800
        assert teuer == pytest.approx(VSPR + 4800, abs=0.01)

    def test_nutzt_die_rv_grenze_nicht_die_kv_grenze(self) -> None:
        """Regressionsschutz für die ZRE4VPR-Falle.

        MVSPKVPV überschreibt ZRE4VPR mit BBGKVPV. MVSPHB muss den Wert
        deshalb NEU mit BBGRVALV berechnen. Der Fall liegt bewusst unter dem
        1.900-Deckel: darüber liefert die falsche Grenze dasselbe Ergebnis,
        und der Test wäre blind.
        """
        assert _BBGRV_JAHR != _BBGKV_JAHR, "Grenzen identisch, Test wäre blind"
        hoch = max(_BBGRV_JAHR, _BBGKV_JAHR) + 20_000
        pkpv_monat = 40_00  # 40 EUR -> VSPKVPV = 480, VSPHB bleibt unter 1.900

        ergebnis = _berechne_vorsorgepauschale(
            hoch,
            2.9,
            0,
            1985,
            False,
            steuerklasse=1,
            pkv=True,
            pkpv_monat_cent=pkpv_monat,
            pkpvagz_monat_cent=0,
            alv_pflichtversichert=True,
        )

        vspr = _BBGRV_JAHR * 9.3 / 100
        vspalv_richtig = AV_AN * _BBGRV_JAHR / 100
        vspkvpv = pkpv_monat * 12 / 100
        assert vspalv_richtig + vspkvpv < _VSPHB_MAX, "Fall liegt über dem Deckel"
        assert ergebnis == pytest.approx(vspr + vspalv_richtig + vspkvpv, abs=0.01)


class TestGkvUnveraendert:
    """MVSPHB bindet bei GKV nur im unteren Band, darüber ändert sich nichts."""

    @pytest.mark.parametrize("brutto", [40_000.0, 60_000.0, 90_000.0])
    def test_hohe_einkommen_bleiben_gleich(self, brutto: float) -> None:
        mit = _berechne_vorsorgepauschale(
            brutto, 2.9, 0, 1985, False, steuerklasse=1, alv_pflichtversichert=True
        )
        ohne = _berechne_vorsorgepauschale(
            brutto, 2.9, 0, 1985, False, steuerklasse=1, alv_pflichtversichert=False
        )
        assert mit == pytest.approx(ohne, abs=0.01)

    def test_niedriges_einkommen_aendert_sich_bewusst(self) -> None:
        """Gegenprobe: im bindenden Band MUSS sich etwas ändern.

        Ohne diesen Fall könnte der Test oben auch bei einem toten
        MVSPHB-Zweig grün sein.
        """
        mit = _berechne_vorsorgepauschale(
            13_200.0, 2.9, 0, 1985, False, steuerklasse=1, alv_pflichtversichert=True
        )
        ohne = _berechne_vorsorgepauschale(
            13_200.0, 2.9, 0, 1985, False, steuerklasse=1, alv_pflichtversichert=False
        )
        assert mit > ohne


# --- End-to-End über die Public-API, Sollwerte aus der BMF-Schnittstelle ---
#
# Brutto jeweils ein glattes Vielfaches von 12, damit der Monatsbetrag, den die
# BMF-Schnittstelle bekommt (LZZ = 2), in ganzen Cent aufgeht.
# (brutto_jahr, stkl, pkpv EUR, pkpvagz EUR, alv, krv, lohnsteuer_monat laut BMF)
_BMF_PKV = [
    (60_000.0, 1, 800, 400, True, True, 831.16),
    (60_000.0, 1, 250, 125, True, True, 915.91),  # MVSPHB bindet
    (60_000.0, 1, 250, 125, False, True, 927.75),  # ALV frei, MVSPHB aus
    (60_000.0, 1, 200, 400, True, True, 949.25),  # Zuschuss > Beitrag
    (90_000.0, 3, 700, 350, True, True, 1101.33),
    (72_000.0, 4, 600, 300, True, True, 1200.16),
    (36_000.0, 5, 500, 250, True, True, 653.66),
    (60_000.0, 6, 800, 0, True, True, 1552.50),
    (120_000.0, 1, 900, 0, False, False, 2849.66),  # KRV = 1, ALV = 1
    (150_000.0, 1, 40, 0, True, True, 3884.66),  # über beiden BBG
]


@pytest.mark.parametrize("brutto,sk,pkpv,agz,alv,krv,bmf", _BMF_PKV)
def test_pkv_gegen_bmf_schnittstelle(
    brutto: float, sk: int, pkpv: int, agz: int, alv: bool, krv: bool, bmf: float
) -> None:
    r = berechne_lohnsteuer_pap(
        brutto_jahr=brutto,
        steuerklasse=sk,
        bundesland="Nordrhein-Westfalen",
        mit_kirchensteuer=False,
        kinder=0,
        geburtsjahr=1990,
        kv_zusatzbeitrag=2.9,
        ist_sachsen=False,
        jahr=2026,
        pkv=True,
        pkpv_monat_cent=pkpv * 100,
        pkpvagz_monat_cent=agz * 100,
        alv_pflichtversichert=alv,
        rv_pflichtversichert=krv,
    )
    assert r["lohnsteuer_monat"] == pytest.approx(bmf, abs=0.011)
