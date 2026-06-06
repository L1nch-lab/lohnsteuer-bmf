"""Einkommensteuer-Berechnungsmodul nach §32a EStG.

Dieses Modul implementiert die Einkommensteuer-Tarifberechnung fuer die
Steuerjahre 2024, 2025 und 2026 gemaess den offiziellen Formeln des
Bundesministeriums der Finanzen (BMF).

Zusaetzlich enthalten:
- Ehegattensplitting (§32a Abs. 5 EStG)
- Solidaritaetszuschlag (§3 SolZG)
- Kirchensteuer (Landeskirchensteuersaetze)

Rechtsgrundlagen:
    - §32a EStG (Einkommensteuertarif)
    - §32a Abs. 5 EStG (Splitting-Verfahren)
    - §3 Solidaritaetszuschlaggesetz (SolZG)
    - Kirchensteuergesetze der Laender

Hinweis:
    Die Koeffizienten basieren auf den offiziellen BMF-Programmablaufplaenen
    (PAP) und dem Gesetzestext des §32a EStG. Die Werte fuer 2025 und 2026
    entsprechen dem Inflationsausgleichsgesetz bzw. Steuerfortentwicklungsgesetz.
    Alle Angaben ohne Gewaehr -- keine Steuerberatung.
"""

from typing import Any, Final

from lohnsteuer_bmf.konstanten import BUNDESLAENDER, UNTERSTUETZTE_JAHRE

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

KIRCHENSTEUER_8_PROZENT: Final[frozenset[str]] = frozenset(
    {
        "Baden-Württemberg",
        "Bayern",
    }
)  # DEPRECATED: Wird durch _data.get_kirchensteuersatz() ersetzt

# Vereinfachte Faktoren Brutto -> zvE je Steuerklasse
# Wird von brutto_netto importiert.
ZVE_FAKTOREN: Final[dict[int, float]] = {
    1: 0.75,
    2: 0.73,
    3: 0.80,
    4: 0.75,
    5: 0.68,
    6: 0.85,
}


# ---------------------------------------------------------------------------
# Einkommensteuer-Tariffunktionen
# ---------------------------------------------------------------------------


def _einkommensteuer_tarif(zve_raw: float, t: dict[str, Any]) -> int:
    """Generische ESt-Berechnung mit Tarif-Koeffizienten aus der Datenschicht.

    Implementiert §32a Abs. 1 EStG:
        Zone 1: zvE <= Grundfreibetrag -> 0
        Zone 2: (zone2_a * y + zone2_b) * y
        Zone 3: (zone3_a * z + zone3_b) * z + zone3_c
        Zone 4: zone4_satz * zvE - zone4_abzug
        Zone 5: zone5_satz * zvE - zone5_abzug

    Args:
        zve_raw: Zu versteuerndes Einkommen in Euro.
        t: Tarif-Dict (get_est_tarif).

    Returns:
        Einkommensteuer in Euro, auf vollen Euro-Betrag abgerundet.
    """
    zve = int(zve_raw)

    if zve <= t["grundfreibetrag"]:
        est = 0.0
    elif zve <= t["zone2_bis"]:
        y = (zve - t["grundfreibetrag"]) / 10_000
        est = (t["zone2_a"] * y + t["zone2_b"]) * y
    elif zve <= t["zone3_bis"]:
        z = (zve - t["zone2_bis"]) / 10_000
        est = (t["zone3_a"] * z + t["zone3_b"]) * z + t["zone3_c"]
    elif zve <= t["zone4_bis"]:
        est = t["zone4_satz"] * zve - t["zone4_abzug"]
    else:
        est = t["zone5_satz"] * zve - t["zone5_abzug"]

    return int(est)


def einkommensteuer(zve: float, jahr: int) -> int:
    """Berechnet die Einkommensteuer fuer ein gegebenes Steuerjahr.

    Laedt Tarif-Koeffizienten aus der Datenschicht und berechnet nach §32a EStG.

    Args:
        zve: Zu versteuerndes Einkommen in Euro.
        jahr: Steuerjahr (2024, 2025 oder 2026).

    Returns:
        Einkommensteuer in Euro, auf vollen Euro-Betrag abgerundet.

    Raises:
        ValueError: Falls das Steuerjahr nicht unterstuetzt wird.
    """
    from lohnsteuer_bmf._data import get_est_tarif

    try:
        tarif = get_est_tarif(jahr)
    except KeyError:
        raise ValueError(
            f"Steuerjahr {jahr} wird nicht unterstuetzt. "
            f"Unterstuetzte Jahre: {', '.join(str(j) for j in UNTERSTUETZTE_JAHRE)}"
        ) from None
    return _einkommensteuer_tarif(zve, tarif)


# ---------------------------------------------------------------------------
# Ehegattensplitting
# ---------------------------------------------------------------------------


def einkommensteuer_splitting(zve: float, jahr: int) -> int:
    """Berechnet die Einkommensteuer im Splitting-Verfahren (Zusammenveranlagung).

    Gemaess §32a Abs. 5 EStG wird das zu versteuernde Einkommen halbiert,
    die Steuer darauf berechnet und anschliessend verdoppelt.

    Das Splitting-Verfahren gilt fuer:
        - Ehegatten (§26b EStG)
        - Eingetragene Lebenspartner

    Args:
        zve: Gemeinsames zu versteuerndes Einkommen beider Ehegatten in Euro.
        jahr: Steuerjahr (2024, 2025 oder 2026).

    Returns:
        Einkommensteuer in Euro, auf vollen Euro-Betrag abgerundet.

    Raises:
        ValueError: Falls das Steuerjahr nicht unterstuetzt wird.
    """
    halbes_zve = zve / 2.0
    steuer_halbe = einkommensteuer(halbes_zve, jahr)
    return steuer_halbe * 2


# ---------------------------------------------------------------------------
# Solidaritaetszuschlag
# ---------------------------------------------------------------------------


def solidaritaetszuschlag(
    est: float,
    zusammenveranlagung: bool = False,
    jahr: int = 2026,
) -> float:
    """Berechnet den Solidaritaetszuschlag gemaess §3 SolZG.

    Der Solidaritaetszuschlag betraegt grundsaetzlich 5,5% der Einkommensteuer.
    Es gelten jedoch Freigrenzen und eine Milderungszone:

    - Liegt die ESt unterhalb der Freigrenze, faellt kein Soli an.
    - In der Milderungszone (knapp ueber der Freigrenze) wird der Soli auf
      maximal 11,9% des ueber die Freigrenze hinausgehenden Betrags begrenzt.
    - Oberhalb der Milderungszone gelten die vollen 5,5%.

    Freigrenzen (Einzelveranlagung / Zusammenveranlagung):
        2024: 18.130 EUR / 36.260 EUR
        2025: 19.950 EUR / 39.900 EUR
        2026: 20.350 EUR / 40.700 EUR

    Args:
        est: Festzusetzende Einkommensteuer in Euro.
        zusammenveranlagung: True bei Zusammenveranlagung (Ehegatten/Lebenspartner).
        jahr: Steuerjahr (2024, 2025 oder 2026).

    Returns:
        Solidaritaetszuschlag in Euro, auf 2 Dezimalstellen gerundet.

    Raises:
        ValueError: Falls das Steuerjahr nicht unterstuetzt wird.
    """
    from lohnsteuer_bmf._data import get_steuerjahr_parameter

    try:
        params = get_steuerjahr_parameter(jahr)
    except KeyError:
        raise ValueError(
            f"Steuerjahr {jahr} wird nicht unterstuetzt. "
            f"Unterstuetzte Jahre: {', '.join(str(j) for j in UNTERSTUETZTE_JAHRE)}"
        ) from None

    freigrenze = (
        params["soli_freigrenze_zusammen"]
        if zusammenveranlagung
        else params["soli_freigrenze_einzel"]
    )

    if est <= freigrenze:
        return 0.0

    soli_voll = est * 0.055
    soli_milderung = (est - freigrenze) * 0.119

    return round(float(min(soli_voll, soli_milderung)), 2)


# ---------------------------------------------------------------------------
# Kirchensteuer
# ---------------------------------------------------------------------------


def kirchensteuer(est: float, bundesland: str) -> float:
    """Berechnet die Kirchensteuer auf Basis der Einkommensteuer.

    Die Kirchensteuer betraegt:
        - 8% der ESt in Bayern und Baden-Wuerttemberg
        - 9% der ESt in allen anderen Bundeslaendern

    Rechtsgrundlage: Jeweiliges Landeskirchensteuergesetz (KiStG).

    Hinweis: Kirchensteuer faellt nur fuer Mitglieder einer steuererhebenden
    Religionsgemeinschaft an. Bei Kirchenaustritt entfaellt die Pflicht
    ab dem Folgemonat.

    Args:
        est: Festzusetzende Einkommensteuer in Euro.
        bundesland: Name des Bundeslandes (z.B. "Bayern", "Berlin").
            Muss einem Eintrag in BUNDESLAENDER entsprechen.

    Returns:
        Kirchensteuer in Euro, auf 2 Dezimalstellen gerundet.

    Raises:
        ValueError: Falls das Bundesland nicht bekannt ist.
    """
    if bundesland not in BUNDESLAENDER:
        raise ValueError(
            f"Unbekanntes Bundesland: '{bundesland}'. Gültige Werte: {', '.join(BUNDESLAENDER)}"
        )

    from lohnsteuer_bmf._data import get_kirchensteuersatz

    satz = get_kirchensteuersatz(bundesland) / 100  # 8.0 → 0.08
    return round(est * satz, 2)
