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
    AV_AN,
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

# Deckel fuer den ALV-Teilbetrag der Vorsorgepauschale, PAP-Modul MVSPHB.
# § 39b Abs. 2 Satz 5 Nr. 3 Buchst. e EStG, woertlich: der Teilbetrag "ist jedoch
# nur anzusetzen, soweit er zusammen mit den Teilbetraegen nach den Buchstaben b
# bis d einen Betrag in Hoehe von 1 900 Euro nicht uebersteigt".
# Am Normtext verifiziert 2026-08-15 (gesetze-im-internet, builddate 20260804).
# Wie _KV_AN_ERMAESSIGT ein im Gesetz fixierter Betrag, kein Jahreswert — daher
# Code-Konstante statt Datenschicht-Parameter.
_VSPHB_MAX = 1900.0

# KV-AN-Satz fuer die VORSORGEPAUSCHALE: §39b Abs. 2 Satz 5 Nr. 3 Buchst. b EStG
# schreibt den ERMAESSIGTEN Beitragssatz vor (§243 SGB V: 14,0 % -> AN-Haelfte
# 7,0 %), NICHT den allgemeinen (14,6 %/7,3 %). Der Satz ist im Gesetz fixiert
# (kein Jahreswert) — daher Code-Konstante statt Datenschicht. Der echte SV-Abzug fuers
# Netto nutzt weiterhin KV_AN_BASIS (7,3) + Zusatzbeitrag/2; nur die
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
    # ⚠️ ZWEITE Stelle mit derselben Logik wie in `berechne_lohnsteuer_pap` — die
    # ausfuehrliche Begruendung steht dort. Kurz: SAP ist in JEDER Steuerklasse
    # 36 EUR, auch in III. § 39b Abs. 2 S. 5 Nr. 2 EStG verweist auf § 10c SATZ 1;
    # die Verdopplung aus Satz 2 gilt nur der Zusammenveranlagung. Das Splitting
    # sitzt im Tarif (KZTAB = 2), nicht im Freibetrag.
    #
    # Beim Fix am 2026-08-15 blieb genau diese Stelle zuerst stehen. Aufgefallen
    # ist es NICHT hier, sondern in der Webapp-Cross-Validation: dort war der Fix
    # schon drin, hier noch nicht, und Abfindung/KUG in StKl III liefen um bis zu
    # 2,16 EUR auseinander. Wer die eine Stelle aendert, aendert immer beide.
    efa = _EFA if steuerklasse == 2 else 0.0
    if steuerklasse == 6:
        anp, sap = 0.0, 0.0
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
        steuerklasse=steuerklasse,
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
    *,
    pkv: bool = False,
    pkpv_monat_cent: int = 0,
    pkpvagz_monat_cent: int = 0,
    alv_pflichtversichert: bool = True,
    rv_pflichtversichert: bool = True,
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
        pkv: True = ausschliesslich privat krankenversichert (PAP-Input PKV=1).
        pkpv_monat_cent: PKV-Basisbeitrag, MONATSbetrag in Cent (PAP: PKPV).
        pkpvagz_monat_cent: steuerfreier AG-Zuschuss, MONATSbetrag in Cent
            (PAP: PKPVAGZ). Wird vom Beitrag abgezogen, Ergebnis nie negativ.
        alv_pflichtversichert: False -> ALV=1, dann entfaellt der
            Hoechstbetragszweig MVSPHB.
        rv_pflichtversichert: False -> KRV=1, dann entfaellt der
            Rentenversicherungs-Teilbetrag VSPR vollstaendig.

    Returns:
        Dict mit lohnsteuer_monat, soli_monat, kirchensteuer_monat.
    """
    # --- MZTABFB: Feste Abzuege (PAP-konform) ---
    #
    # ⚠️ SAP ist in JEDER Steuerklasse 36 EUR, auch in Klasse III. Bis 2026-08-15
    # stand hier `_SAP * 2  # Verdoppelt bei Splitting` — das war die Logik der
    # VERANLAGUNG, im Lohnsteuerabzug hat sie nichts verloren:
    #
    #   § 39b Abs. 2 S. 5 Nr. 2 EStG zieht "den Sonderausgaben-Pauschbetrag
    #   (§ 10c SATZ 1) in den Steuerklassen I bis V" ab. Der Klammerverweis geht
    #   auf Satz 1 = 36 EUR. § 10c Satz 2 (Verdopplung bei Zusammenveranlagung)
    #   ist bewusst NICHT referenziert.
    #
    #   Das Splitting sitzt stattdessen im TARIF: § 39b Abs. 2 S. 6 rechnet
    #   Steuerklasse III nach § 32a Abs. 5 — im PAP der Faktor KZTAB = 2 in
    #   UPMLST (Anlage 1 S. 25). Wer zusaetzlich den Freibetrag verdoppelt,
    #   zieht denselben Vorteil zweimal.
    #
    # Der PAP schreibt in MZTABFB (Anlage 1 S. 22) in jedem Zweig flach SAP = 36.
    # Fehlerbild vor dem Fix: StKl III rechnete 36 EUR/Jahr zu viel ab, die
    # Lohnsteuer lag rund 0,50 bis 0,83 EUR/Monat unter dem BMF-Rechner.
    efa = _EFA if steuerklasse == 2 else 0.0
    if steuerklasse == 6:
        # SK6: Kein ANP, kein SAP — § 39b Abs. 2 S. 5 Nr. 1 und 2 gelten nur
        # "in den Steuerklassen I bis V".
        anp = 0.0
        sap = 0.0
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
        steuerklasse=steuerklasse,
        pkv=pkv,
        pkpv_monat_cent=pkpv_monat_cent,
        pkpvagz_monat_cent=pkpvagz_monat_cent,
        alv_pflichtversichert=alv_pflichtversichert,
        rv_pflichtversichert=rv_pflichtversichert,
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
    """PAP UP5_6 (Anlage 1 S. 30): Differenzmethode fuer SK V/VI.

    Berechnet: (EST(1.25*ZX) - EST(0.75*ZX)) * 2, mindestens 14 % von ZX.

    Die Trunkierung von `zx * 1.25` und `zx * 0.75` uebernimmt `einkommensteuer()`
    selbst (`int(zve_raw)`, § 32a Abs. 1 EStG "abgerundetes zvE"). MIST dagegen
    braucht sie hier: die PAP-Variablenliste fuehrt `MIST Mindeststeuer fuer die
    Steuerklassen V und VI in EURO` — ohne Cent, anders als `X`, das dort
    ausdruecklich "Euro, Cent (2 Dezimalstellen)" traegt. Das Diagramm setzt den
    Euro-Marker entsprechend an `MIST = ZX * 0,14`.
    """
    st1 = float(einkommensteuer(zx * 1.25, jahr))
    st2 = float(einkommensteuer(zx * 0.75, jahr))
    diff = (st1 - st2) * 2
    mist = float(int(zx * 0.14))
    return max(diff, mist)


def _mst5_6(zve: float, jahr: int) -> float:
    """PAP MST5_6 (Anlage 1 S. 29): Lohnsteuer fuer Steuerklasse V und VI.

    Stufenberechnung mit den Schwellenwerten W1/W2/W3, § 39b Abs. 2 S. 7 EStG.

    ⚠️ Trunkierung nachgezogen 2026-08-15. `ZZX` und `ST` sind in der
    PAP-Variablenliste "in Euro" deklariert, ohne Cent; im Diagramm haengt an
    jedem ST-Aufschlag ein Euro-Marker. Ohne diese Abrundungen lag die Lohnsteuer
    in StKl V/VI rund 0,03 bis 0,11 EUR/Monat ueber dem BMF-Rechner — klein, aber
    systematisch in eine Richtung.
    """
    if zve <= 0:
        return 0.0

    # ZZX = X, deklariert "in Euro" -> auf volle Euro abgerundet.
    zzx = float(int(zve))

    if zzx > _W2STKL5:
        # Stufe 1: UP5_6 auf W2
        st = _up5_6(_W2STKL5, jahr)

        if zzx > _W3STKL5:
            # Stufe 2+3: Spitzen- und Reichensteuer
            st = float(int(st + (_W3STKL5 - _W2STKL5) * 0.42))
            st = float(int(st + (zzx - _W3STKL5) * 0.45))
        else:
            # Stufe 2: Spitzensteuersatz
            st = float(int(st + (zzx - _W2STKL5) * 0.42))
    else:
        # Unter W2: UP5_6 auf ZZX
        st = _up5_6(zzx, jahr)

        if zzx > _W1STKL5:
            # Vergleichsberechnung: UP5_6(W1) + 42 % Aufschlag, kleinerer Wert gewinnt
            vergl = st
            hoch = float(int(_up5_6(_W1STKL5, jahr) + (zzx - _W1STKL5) * 0.42))
            st = min(vergl, hoch)

    return st


def _berechne_vorsorgepauschale(
    brutto_jahr: float,
    kv_zusatzbeitrag: float,
    kinder: int,
    geburtsjahr: int,
    ist_sachsen: bool,
    pv_basissatz: bool = False,
    *,
    steuerklasse: int = 1,
    pkv: bool = False,
    pkpv_monat_cent: int = 0,
    pkpvagz_monat_cent: int = 0,
    alv_pflichtversichert: bool = True,
    rv_pflichtversichert: bool = True,
) -> float:
    """Berechnet die Vorsorgepauschale nach PAP UPEVP + MVSPKVPV + MVSPHB.

    Die drei PAP-Module stehen unten als eigene Bloecke, in derselben Reihenfolge
    wie im Ablaufplan (Anlage 1, Seiten 26 / 27 / 28) — so ist der Code direkt
    gegen die Diagramme pruefbar.

    Rechtsgrundlage: § 39b Abs. 2 Satz 5 Nr. 3 EStG.
        Buchst. a      -> VSPR   (Rentenversicherung)
        Buchst. b - d  -> VSPKVPV (Kranken- + Pflegeversicherung)
        Buchst. e      -> MVSPHB (Hoechstbetrag ueber die Arbeitslosenversicherung)

    PKV (privat krankenversichert): `PKPV` ist der monatliche Basisbeitrag in Cent,
    `PKPVAGZ` der steuerfreie AG-Zuschuss in Cent. Der PAP kennt 2026 nur PKV 0/1;
    das alte "2 = privat mit Zuschuss" gibt es nicht mehr.

    ABWEICHUNG, bewusst und unveraendert: Der PAP rundet an mehreren Stellen auf
    volle Euro ab ("Euro"-Marker im Diagramm). Dieses Modul rechnet durchgehend in
    float ohne diese Trunkierung — das ist der Stand des gesamten Moduls, nicht
    dieser Funktion, und wird hier nicht einseitig geaendert.
    """
    # --- UPEVP (S. 26): Rentenversicherungs-Teilbetrag -------------------------
    # KRV ist der PAP-Merker fuer diesen Teilbetrag (Anlage 1 S. 5, wortgleich):
    #   0 = pflichtversichert in der gesetzlichen RV ODER in einer berufsstaendischen
    #       Versorgungseinrichtung ODER bei Befreiung freiwillig versichert;
    #       es gilt die allgemeine Beitragsbemessungsgrenze
    #   1 = wenn nicht 0
    # Bei KRV = 1 setzt der Ablaufplan VSPR = 0 (S. 26, Ja-Zweig der Abfrage
    # "KRV = 1"; Zweigrichtung an den Wortkoordinaten der Seite geprueft, nicht
    # aus der Textextraktion geraten). Deckt sich mit § 39b Abs. 2 S. 5 Nr. 3
    # Buchst. a EStG, der den Teilbetrag nur Arbeitnehmern gibt, die in der
    # gesetzlichen RV pflichtversichert oder nach § 6 Abs. 1 Nr. 1 SGB VI
    # befreit sind.
    #
    # Das ist der teuerste der drei Schalter: bei 60.000 EUR Brutto sind
    # 9,3 % davon rund 5.580 EUR Vorsorgepauschale, die ersatzlos wegfallen.
    if rv_pflichtversichert:
        # ZRE4VPR wird hier mit BBGRVALV gekappt.
        zre4vpr_rv = min(brutto_jahr, _BBGRV_JAHR)
        vspr = zre4vpr_rv * RV_AN / 100  # 9,3 %
    else:
        vspr = 0.0

    # --- MVSPKVPV (S. 27): Kranken- + Pflegeversicherung -----------------------
    # ACHTUNG: Der PAP belegt ZRE4VPR hier NEU, mit der KV/PV-Grenze BBGKVPV.
    # Der Wert aus UPEVP ist ab hier ueberschrieben — deshalb rechnet MVSPHB
    # weiter unten seine eigene Kappung noch einmal.
    zre4vpr_kv = min(brutto_jahr, _BBGKV_JAHR)

    if pkv:
        # Der STKL-6-Zweig haengt im PAP am PKV-Zweig, NICHT am Modul-Eingang.
        # Bei gesetzlich Versicherten wird die Steuerklasse hier nicht geprueft;
        # diese Asymmetrie steht so im Ablaufplan und wird nicht geglaettet.
        if steuerklasse == 6:
            vspkvpv = 0.0
        else:
            # Reihenfolge wie im PAP: erst der Zuschuss, dann der Beitrag.
            # /100 ist die Cent-zu-Euro-Wandlung, *12 der Jahresbetrag.
            pkpvagzj = pkpvagz_monat_cent * 12 / 100
            vspkvpv = pkpv_monat_cent * 12 / 100
            vspkvpv = vspkvpv - pkpvagzj
            if vspkvpv < 0:
                # Zuschuss groesser als Beitrag: keine negative Pauschale.
                vspkvpv = 0.0
    else:
        # ERMAESSIGTER KV-Satz 7,0 % (§ 39b Abs. 2 S. 5 Nr. 3 b EStG i.V.m.
        # § 243 SGB V), nicht der allgemeine 7,3 % — siehe _KV_AN_ERMAESSIGT.
        kv_satz = _KV_AN_ERMAESSIGT + kv_zusatzbeitrag / 2  # AN-Haelfte
        pv_satz = _berechne_pv_satz(kinder, geburtsjahr, ist_sachsen, pv_basissatz)
        vspkvpv = zre4vpr_kv * (kv_satz + pv_satz) / 100

    vsp = vspkvpv + vspr

    # --- MVSPHB (S. 28): Hoechstbetrag ueber die Arbeitslosenversicherung ------
    # Aufrufbedingung aus UPEVP: nur bei ALV != 1 UND STKL != 6.
    if alv_pflichtversichert and steuerklasse != 6:
        # ZRE4VPR NEU berechnen. Wer hier zre4vpr_kv wiederverwendet, nimmt die
        # KV/PV-Grenze statt der RV/ALV-Grenze — das Ergebnis ist dann zu klein,
        # aber nicht offensichtlich falsch.
        zre4vpr_alv = min(brutto_jahr, _BBGRV_JAHR)
        vspalv = AV_AN * zre4vpr_alv / 100
        vsphb = vspalv + vspkvpv
        if vsphb > _VSPHB_MAX:
            vsphb = _VSPHB_MAX
        vspn = vspr + vsphb
        if vspn > vsp:
            vsp = vspn

    return vsp


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
