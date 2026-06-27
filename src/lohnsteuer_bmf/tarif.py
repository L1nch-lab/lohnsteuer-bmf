"""Einkommensteuer-Tarif — reiner Tarif-Endpoint.

Berechnet die Einkommensteuer, Solidaritaetszuschlag und optional
Kirchensteuer aus dem zu versteuernden Einkommen (zvE).

Liefert zusaetzlich Grenzsteuersatz und Durchschnittssteuersatz.
"""

from typing import Any

from lohnsteuer_bmf.einkommensteuer import (
    einkommensteuer,
    einkommensteuer_splitting,
    solidaritaetszuschlag,
)
from lohnsteuer_bmf.einkommensteuer import (
    kirchensteuer as berechne_kirchensteuer,
)


def _lade_grundfreibetraege() -> dict[int, int]:
    """Laedt Grundfreibetraege aus der Datenschicht."""
    from lohnsteuer_bmf._data import get_est_tarif

    result: dict[int, int] = {}
    for jahr in (2024, 2025, 2026):
        t = get_est_tarif(jahr)
        result[jahr] = t["grundfreibetrag"]
    return result


def _lade_tarifzonen() -> dict[int, list[tuple[int, str, str]]]:
    """Laedt Tarifzonen-Grenzen aus der Datenschicht."""
    from lohnsteuer_bmf._data import get_est_tarif

    result: dict[int, list[tuple[int, str, str]]] = {}
    for jahr in (2024, 2025, 2026):
        t = get_est_tarif(jahr)
        result[jahr] = [
            (t["grundfreibetrag"], "Grundfreibetrag", "0 %"),
            (t["zone2_bis"], "Untere Progressionszone", "14–24 %"),
            (t["zone3_bis"], "Obere Progressionszone", "24–42 %"),
            (t["zone4_bis"], "Spitzensteuersatz", "42 %"),
            (0, "Reichensteuer", "45 %"),
        ]
    return result


_GRUNDFREIBETRAEGE: dict[int, int] = _lade_grundfreibetraege()
_TARIFZONEN: dict[int, list[tuple[int, str, str]]] = _lade_tarifzonen()


def _grenzsteuersatz(zve: float, jahr: int, splitting: bool) -> float:
    """Berechnet den Grenzsteuersatz (marginale Steuerbelastung).

    Methode: (ESt(zvE+100) - ESt(zvE)) / 100 * 100.
    Delta von 100 EUR statt 1 EUR, weil einkommensteuer() auf int abrundet.
    """
    est_fn = einkommensteuer_splitting if splitting else einkommensteuer
    delta = 100
    est_basis = est_fn(zve, jahr)
    est_plus = est_fn(zve + delta, jahr)
    return round((est_plus - est_basis) / delta * 100, 2)


def _tarifzone(zve: float, jahr: int) -> dict[str, int | str]:
    """Bestimmt die aktuelle Tarifzone."""
    zonen = _TARIFZONEN.get(jahr, _TARIFZONEN[2026])
    for i, (grenze, name, satz) in enumerate(zonen):
        if i == len(zonen) - 1:
            # Letzte Zone (Reichensteuer) — keine Obergrenze
            return {"zone": i + 1, "name": name, "satz": satz}
        if zve <= grenze:
            return {"zone": i + 1, "name": name, "satz": satz}
    # Unerreichbar: die letzte Zone returnt oben immer (i == len-1); nur als
    # Fallback, falls _TARIFZONEN je leer wäre.
    return {"zone": 5, "name": "Reichensteuer", "satz": "45 %"}  # pragma: no cover


def berechne_einkommensteuer_tarif(
    zve: float,
    zusammenveranlagung: bool = False,
    kirchensteuer: bool = False,
    bundesland: str = "Nordrhein-Westfalen",
    jahr: int = 2026,
) -> dict[str, Any]:
    """Berechnet ESt, Soli, KiSt und Steuersaetze aus dem zvE.

    Args:
        zve: Zu versteuerndes Einkommen in EUR.
        zusammenveranlagung: True fuer Ehegattensplitting.
        kirchensteuer: True fuer Kirchensteuer.
        bundesland: Bundesland (fuer Kirchensteuersatz).
        jahr: Steuerjahr (2024-2026).

    Returns:
        Dict mit ESt, Soli, KiSt, Grenz-/Durchschnittssteuersatz, Tarifzone.
    """
    est_fn = einkommensteuer_splitting if zusammenveranlagung else einkommensteuer
    est = est_fn(zve, jahr)

    soli = solidaritaetszuschlag(
        est,
        zusammenveranlagung=zusammenveranlagung,
        jahr=jahr,
    )

    kist = 0.0
    if kirchensteuer:
        kist = berechne_kirchensteuer(est, bundesland)

    steuer_gesamt = round(est + soli + kist, 2)

    # Grenzsteuersatz
    grenzsteuersatz = _grenzsteuersatz(zve, jahr, zusammenveranlagung)

    # Durchschnittssteuersatz (nur ESt, ohne Soli/KiSt)
    if zve > 0:
        durchschnittssteuersatz = round(est / zve * 100, 2)
        belastungsquote = round(steuer_gesamt / zve * 100, 2)
    else:
        durchschnittssteuersatz = 0.0
        belastungsquote = 0.0

    # Tarifzone bestimmen (bei Splitting: halbes zvE fuer Zonenbestimmung)
    zone_zve = zve / 2 if zusammenveranlagung else zve
    zone = _tarifzone(zone_zve, jahr)

    grundfreibetrag = _GRUNDFREIBETRAEGE.get(jahr, _GRUNDFREIBETRAEGE[2026])
    if zusammenveranlagung:
        grundfreibetrag *= 2

    return {
        "zve": zve,
        "einkommensteuer": float(est),
        "solidaritaetszuschlag": soli,
        "kirchensteuer": kist,
        "steuer_gesamt": steuer_gesamt,
        "grenzsteuersatz": grenzsteuersatz,
        "durchschnittssteuersatz": durchschnittssteuersatz,
        "belastungsquote": belastungsquote,
        "tarifzone": zone,
        "grundfreibetrag": grundfreibetrag,
        "zusammenveranlagung": zusammenveranlagung,
        "steuerjahr": jahr,
    }
