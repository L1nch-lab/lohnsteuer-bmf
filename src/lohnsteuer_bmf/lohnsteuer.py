"""Lohnsteuer-Berechnung nach BMF Programmablaufplan 2026.

Implementiert die offizielle zvE-Berechnung (zu versteuerndes Einkommen)
aus dem Bruttolohn inkl. Vorsorgepauschale, Werbungskosten-Pauschbetrag,
Sonderausgaben-Pauschbetrag und Entlastungsbetrag.

Ersetzt die vereinfachten ZVE_FAKTOREN durch die PAP-konforme Logik.

Rechtsgrundlage:
    BMF Programmablaufplan 2026 (BMF-Schreiben vom 12.11.2025,
    IV C 5 - S 2361/00025/016/028)
"""

from lohnsteuer_bmf._data import get_steuerjahr_parameter as _get_stp
from lohnsteuer_bmf.einkommensteuer import (
    einkommensteuer,
    solidaritaetszuschlag,
)
from lohnsteuer_bmf.einkommensteuer import (
    kirchensteuer as berechne_kirchensteuer,
)
from lohnsteuer_bmf.konstanten import (
    BBG_KV_PV_MONAT,
    BBG_RV_AV_MONAT,
    KV_ZUSATZBEITRAG_DEFAULT,
    PV_AN_BASIS,
    PV_AN_BASIS_SACHSEN,
    PV_KIND_ABSCHLAG,
    PV_KINDERLOS_ZUSCHLAG,
    RV_AN,
)

# ---------------------------------------------------------------------------
# PAP-Konstanten (aus der Datenschicht, Jahr 2026)
# ---------------------------------------------------------------------------

_P = _get_stp(2026)

# Beitragsbemessungsgrenzen (jaehrlich)
_BBGRV_JAHR = BBG_RV_AV_MONAT * 12
_BBGKV_JAHR = BBG_KV_PV_MONAT * 12

# Pauschbetraege
_ANP = _P["anp"]
_SAP = _P["sap"]
_EFA = _P["efa"]

# Kinderfreibetrag (§32 Abs. 6 EStG)
_KFB_VOLL = _P["kfb_voll"]
_KFB_HALB = _P["kfb_halb"]

# Vorsorgepauschale Hoechstbetrag (§10 Abs. 4 EStG)
_VSPMAX_SK1 = _P["vspmax_sk1"]
_VSPMAX_SK3 = _P["vspmax_sk3"]

# KV-AN-Satz fuer die VORSORGEPAUSCHALE: §39b Abs. 2 Satz 5 Nr. 3 Buchst. b EStG
# schreibt den ERMAESSIGTEN Beitragssatz vor (§243 SGB V: 14,0 % -> AN-Haelfte
# 7,0 %), NICHT den allgemeinen (14,6 %/7,3 %). Der Satz ist im Gesetz fixiert
# (kein Jahreswert) — daher Code-Konstante statt Datenschicht. Der echte SV-Abzug
# fuers Netto nutzt weiterhin KV_AN_BASIS (7,3) + Zusatzbeitrag/2; nur die
# LSt-Typisierung rechnet ermaessigt. Fix 2026-07-14 (Upstream): vorher stand hier
# KV_AN_BASIS -> LSt systematisch bis ~88-94 EUR/Jahr zu niedrig (BMF-Diff
# 7,33/Monat ab BBG-KV). Verifiziert gegen bmf-steuerrechner.de (102 Faelle).
_KV_AN_ERMAESSIGT = 7.0


def berechne_zve(
    brutto_jahr: float,
    steuerklasse: int,
    kinder: int = 0,
    geburtsjahr: int = 1985,
    ist_sachsen: bool = False,
    kv_zusatzbeitrag: float = KV_ZUSATZBEITRAG_DEFAULT,
    pv_basissatz: bool = False,
) -> float:
    """Berechnet das zu versteuernde Einkommen (zvE) aus dem Bruttolohn.

    PAP-konform: Brutto - ANP - SAP - EFA - Vorsorgepauschale.
    Nutzbar fuer alle Module die zvE aus Brutto benoetigen.
    """
    efa = _EFA if steuerklasse == 2 else 0.0
    if steuerklasse == 6:
        anp, sap = 0.0, 0.0
    elif steuerklasse == 3:
        anp, sap = _ANP, _SAP * 2
    else:
        anp, sap = _ANP, _SAP

    ztabfb = efa + anp + sap
    vsp = _berechne_vorsorgepauschale(
        brutto_jahr,
        kv_zusatzbeitrag,
        kinder,
        geburtsjahr,
        ist_sachsen,
        pv_basissatz,
    )
    return max(0.0, brutto_jahr - ztabfb - vsp)


def berechne_lohnsteuer_pap(
    brutto_jahr: float,
    steuerklasse: int,
    bundesland: str,
    mit_kirchensteuer: bool,
    kinder: int,
    geburtsjahr: int,
    kv_zusatzbeitrag: float,
    ist_sachsen: bool,
    jahr: int = 2026,
) -> dict[str, float]:
    """Berechnet Lohnsteuer nach offiziellem BMF PAP.

    Args:
        brutto_jahr: Jahres-Bruttolohn in EUR.
        steuerklasse: Steuerklasse 1-6.
        bundesland: Bundesland (fuer KiSt-Satz).
        mit_kirchensteuer: Kirchensteuerpflicht.
        kinder: Anzahl Kinder (fuer KFB bei Soli/KiSt).
        geburtsjahr: Geburtsjahr (fuer PV-Kinderlos-Zuschlag).
        kv_zusatzbeitrag: KV-Zusatzbeitrag in Prozent.
        ist_sachsen: Sachsen-Sonderregel PV.
        jahr: Steuerjahr.

    Returns:
        Dict mit lohnsteuer_monat, soli_monat, kirchensteuer_monat.
    """
    # --- MZTABFB: Feste Abzuege (PAP-konform) ---
    efa = _EFA if steuerklasse == 2 else 0.0
    if steuerklasse == 6:
        # SK6: Kein ANP, kein SAP (zweites Dienstverhaeltnis)
        anp = 0.0
        sap = 0.0
    elif steuerklasse == 3:
        anp = _ANP
        sap = _SAP * 2  # Verdoppelt bei Splitting
    else:
        anp = _ANP
        sap = _SAP

    # Kinderfreibetrag (nur fuer Soli/KiSt-Berechnung, NICHT fuer EST)
    if steuerklasse == 3:
        kfb = kinder * _KFB_VOLL
    elif steuerklasse in (1, 2, 4):
        kfb = kinder * _KFB_HALB
    else:
        kfb = 0.0  # SK 5, 6: kein KFB

    ztabfb = efa + anp + sap  # Feste Tabellenfreibetraege

    # --- UPEVP: Vorsorgepauschale ---
    vsp = _berechne_vorsorgepauschale(
        brutto_jahr,
        kv_zusatzbeitrag,
        kinder,
        geburtsjahr,
        ist_sachsen,
    )

    # --- MLSTJAHR: zvE berechnen ---
    zre4 = brutto_jahr  # Vereinfacht: keine Versorgungsbezuege/Altersentlastung
    zve = max(0.0, zre4 - ztabfb - vsp)

    # --- UPMLST: Steuerberechnung ---
    splitting = steuerklasse == 3
    if steuerklasse in (1, 2, 3, 4):
        # Standard-Tarif (SK3 = Splitting)
        x = zve / 2 if splitting else zve
        est_jahr = float(einkommensteuer(x, jahr))
        if splitting:
            est_jahr *= 2
    else:
        # SK 5/6: Spezialberechnung MST5_6 (Differenzmethode)
        est_jahr = _mst5_6(zve, jahr)

    lohnsteuer_monat = round(est_jahr / 12, 2)

    # --- MSOLZ: Solidaritaetszuschlag ---
    # Bemessungsgrundlage = EST auf zvE abzueglich Kinderfreibetrag
    # Fuer SK5/6 muss MST5_6 verwendet werden (nicht Grundtarif)
    zve_fuer_soli = max(0.0, zve - kfb)
    if splitting:
        x_soli = zve_fuer_soli / 2
        est_soli = float(einkommensteuer(x_soli, jahr)) * 2
    elif steuerklasse in (5, 6):
        est_soli = _mst5_6(zve_fuer_soli, jahr)
    else:
        est_soli = float(einkommensteuer(zve_fuer_soli, jahr))

    soli_jahr = solidaritaetszuschlag(est_soli, zusammenveranlagung=splitting, jahr=jahr)
    soli_monat = round(soli_jahr / 12, 2)

    # --- Kirchensteuer ---
    if mit_kirchensteuer:
        kist_jahr = berechne_kirchensteuer(est_soli, bundesland)
        kirchensteuer_monat = round(kist_jahr / 12, 2)
    else:
        kirchensteuer_monat = 0.0

    return {
        "lohnsteuer_monat": lohnsteuer_monat,
        "soli_monat": soli_monat,
        "kirchensteuer_monat": kirchensteuer_monat,
        "zve_jahr": round(zve, 2),
        "vorsorgepauschale": round(vsp, 2),
    }


# PAP-Konstanten fuer MST5_6 (Steuerklasse V/VI) — aus der Datenschicht
_W1STKL5 = _P["w1stkl5"]
_W2STKL5 = _P["w2stkl5"]
_W3STKL5 = _P["w3stkl5"]


def _up5_6(zx: float, jahr: int) -> float:
    """PAP UP5_6: Differenzmethode fuer SK V/VI.

    Berechnet: (EST(1.25*ZX) - EST(0.75*ZX)) * 2
    Minimum: 14% von ZX.
    """
    st1 = float(einkommensteuer(zx * 1.25, jahr))
    st2 = float(einkommensteuer(zx * 0.75, jahr))
    diff = (st1 - st2) * 2
    mist = zx * 0.14
    return max(diff, mist)


def _mst5_6(zve: float, jahr: int) -> float:
    """PAP MST5_6: Lohnsteuer fuer Steuerklasse V und VI.

    Stufenberechnung mit Schwellenwerten W1/W2/W3.
    """
    if zve <= 0:
        return 0.0

    zzx = zve

    if zzx > _W2STKL5:
        # Stufe 1: UP5_6 auf W2
        st = _up5_6(_W2STKL5, jahr)

        if zzx > _W3STKL5:
            # Stufe 2+3: Spitzen- und Reichensteuer
            st += (_W3STKL5 - _W2STKL5) * 0.42
            st += (zzx - _W3STKL5) * 0.45
        else:
            # Stufe 2: Spitzensteuersatz
            st += (zzx - _W2STKL5) * 0.42
    else:
        # Unter W2: UP5_6 auf ZZX
        st = _up5_6(zzx, jahr)

        if zzx > _W1STKL5:
            # Vergleichsberechnung: UP5_6(W1) + 42% Aufschlag
            vergl = st
            hoch = _up5_6(_W1STKL5, jahr) + (zzx - _W1STKL5) * 0.42
            st = min(vergl, hoch)

    return st


def _berechne_vorsorgepauschale(
    brutto_jahr: float,
    kv_zusatzbeitrag: float,
    kinder: int,
    geburtsjahr: int,
    ist_sachsen: bool,
    pv_basissatz: bool = False,
) -> float:
    """Berechnet die Vorsorgepauschale nach PAP UPEVP/MVSPKVPV.

    Bei gesetzlicher Krankenversicherung (PKV=0):
    VSP = VSPR (RV-Beitrag) + VSPKVPV (KV+PV-Beitrag)

    BEWUSSTE PAP-VEREINFACHUNG (dokumentiert, kein Bug): Der §39b Abs. 2 Satz 5 Nr. 3
    Buchstabe e EStG-Zweig (PAP-Modul MVSPHB: VSP = max(VSP, VSPR + min(VSPALV+VSPKVPV,
    1.900))) fehlt hier. Real-Impact ~0 EUR (wirkt nur wo VSPKVPV < 1.900, dort zvE < GFB
    → Lohnsteuer 0; Extremfall ~34 EUR/Jahr, bei Veranlagung ausgeglichen).
    Beleg: §39b Abs. 2 Satz 5 Nr. 3 Buchstabe e EStG (gesetze-im-internet.de/estg/__39b.html)
    + BMF-Programmablaufplan (Modul MVSPHB, Höchstbetragsberechnung).

    Bei SK6: kein RV-Abzug.
    """
    # 1. Rentenversicherung (VSPR) — PAP: abhaengig von KRV Input
    # KRV=0 (RV-pflichtig): voller RV-Abzug, auch bei SK6
    # Die VSP haengt NICHT von der Steuerklasse ab (PAP UPEVP)
    rv_basis = min(brutto_jahr, _BBGRV_JAHR)
    vspr = rv_basis * RV_AN / 100  # 9.3%

    # 2. KV + PV (MVSPKVPV) — gesetzlich versichert (PKV=0)
    # ERMAESSIGTER Satz 7,0 % (§39b Abs. 2 S. 5 Nr. 3 b EStG i.V.m. §243 SGB V),
    # nicht der allgemeine 7,3 %! Siehe _KV_AN_ERMAESSIGT-Kommentar oben.
    kv_basis = min(brutto_jahr, _BBGKV_JAHR)
    kv_satz = _KV_AN_ERMAESSIGT + kv_zusatzbeitrag / 2  # AN-Haelfte
    pv_satz = _berechne_pv_satz(kinder, geburtsjahr, ist_sachsen, pv_basissatz)
    vspkvpv = kv_basis * (kv_satz + pv_satz) / 100

    # Gesamte Vorsorgepauschale. ALV-Teilbetrag + §39b lit. e 1.900-EUR-Cap
    # (PAP-Modul MVSPHB) bewusst weggelassen — siehe Docstring (~0 EUR Impact).
    return vspr + vspkvpv


def _berechne_pv_satz(
    kinder: int, geburtsjahr: int, ist_sachsen: bool, pv_basissatz: bool = False
) -> float:
    """PV-AN-Beitragssatz in Prozent (identisch mit brutto_netto.py).

    pv_basissatz=True erzwingt den Basissatz nach § 55 Abs. 1 S. 1 SGB XI — ohne
    Kinderlosenzuschlag und ohne Kinder-Abschlaege (§ 55 Abs. 3). Gebraucht fuer das
    KUG-Leistungsentgelt: § 153 Abs. 1 S. 4 Nr. 3 SGB III schreibt genau diesen Satz vor.
    """
    basis = PV_AN_BASIS_SACHSEN if ist_sachsen else PV_AN_BASIS
    if pv_basissatz:
        return basis
    alter_2026 = 2026 - geburtsjahr

    if kinder == 0 and alter_2026 > 23:
        return basis + PV_KINDERLOS_ZUSCHLAG

    if kinder <= 1:
        return basis

    zusatz_kinder = min(kinder, 5) - 1
    return max(basis - zusatz_kinder * PV_KIND_ABSCHLAG, 0.0)
