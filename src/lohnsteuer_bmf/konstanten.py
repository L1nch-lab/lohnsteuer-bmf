"""Geteilte Konstanten für lohnsteuer-bmf.

Vereint die allgemeinen Konstanten (Bundesländer, unterstützte Steuerjahre) und
die Sozialversicherungs-Konstanten (Beitragssätze, Beitragsbemessungsgrenzen)
für das Steuerjahr 2026.

Carve-out aus rechner-hub-api/steuerlogik (constants.py + sv_konstanten.py).
Nur die Daten-Schicht (ehemals db.py/SQLite) wurde durch _data.py ersetzt —
die Berechnungslogik und die Werte sind unverändert.

Rechtsgrundlagen (SV):
    - Sozialversicherungs-Rechengrößenverordnung (jährlich)
    - SGB V §§ 220, 241, 249 (Krankenversicherung)
    - SGB XI §§ 55, 58 (Pflegeversicherung)
    - SGB VI §§ 157, 158, 159 (Rentenversicherung)
    - SGB III §§ 341, 346 (Arbeitslosenversicherung)
"""

from typing import Any, Final

from lohnsteuer_bmf._data import (
    get_alle_bundeslaender,
    get_pv_ag,
    get_pv_an_basis,
    get_steuerjahr_parameter,
)

# ---------------------------------------------------------------------------
# Allgemeine Konstanten
# ---------------------------------------------------------------------------

# Alle 16 Bundesländer
BUNDESLAENDER: Final[tuple[str, ...]] = (
    "Baden-Württemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thüringen",
)

# Unterstützte Steuerjahre (ESt-Tarif)
UNTERSTUETZTE_JAHRE: Final[tuple[int, ...]] = (2024, 2025, 2026)

# Aktuelles Default-Steuerjahr
AKTUELLES_STEUERJAHR: Final[int] = 2026

# Validierung: BUNDESLAENDER muss mit der Datenschicht übereinstimmen
assert set(BUNDESLAENDER) == set(get_alle_bundeslaender()), (  # noqa: S101
    f"BUNDESLAENDER Tuple ({len(BUNDESLAENDER)}) stimmt nicht mit _data "
    f"({len(get_alle_bundeslaender())}) überein!"
)

# ---------------------------------------------------------------------------
# Sozialversicherungs-Konstanten (Steuerjahr 2026)
# ---------------------------------------------------------------------------

_P: Final[dict[str, Any]] = get_steuerjahr_parameter(2026)

# Beitragsbemessungsgrenzen (monatlich)
BBG_KV_PV_MONAT: Final[float] = _P["bbg_kv_pv_monat"]
BBG_RV_AV_MONAT: Final[float] = _P["bbg_rv_av_monat"]

# Beitragssätze AN-Anteil (Prozent, z.B. 7.3 = 7.3%)
KV_AN_BASIS: Final[float] = _P["kv_an_basis"]
KV_ZUSATZBEITRAG_DEFAULT: Final[float] = _P["kv_zusatzbeitrag"]

PV_AN_BASIS: Final[float] = _P["pv_an_basis"]
PV_AN_BASIS_SACHSEN: Final[float] = get_pv_an_basis("Sachsen")
PV_KINDERLOS_ZUSCHLAG: Final[float] = _P["pv_kinderlos_zuschlag"]
PV_KIND_ABSCHLAG: Final[float] = _P["pv_kind_abschlag"]

RV_AN: Final[float] = _P["rv_an"]
AV_AN: Final[float] = _P["av_an"]

# Beitragssätze AG-Anteil (Prozent)
KV_AG_BASIS: Final[float] = _P["kv_ag_basis"]
KV_AG_ZUSATZ_ANTEIL: Final[float] = _P["kv_ag_zusatz_anteil"]

PV_AG: Final[float] = get_pv_ag("Bayern")  # alle Nicht-Sachsen-BL haben 1.8
PV_AG_SACHSEN: Final[float] = get_pv_ag("Sachsen")

RV_AG: Final[float] = _P["rv_ag"]
AV_AG: Final[float] = _P["av_ag"]

AG_UMLAGE_SATZ: Final[float] = _P["ag_umlage_satz"]

# Minijob/Midijob-Grenzen
MINIJOB_GRENZE: Final[float] = _P["minijob_grenze"]
MIDIJOB_OBERGRENZE: Final[float] = _P["midijob_obergrenze"]
MINDESTLOHN: Final[float] = _P["mindestlohn"]
