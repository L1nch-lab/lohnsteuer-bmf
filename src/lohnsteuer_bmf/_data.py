"""Inline-Datenschicht für lohnsteuer-bmf (ersetzt den db.py/SQLite-Slice).

GENERIERT von tools/sync_from_upstream.py aus rechner-hub-api/steuerlogik/data/rechner.db.
NICHT von Hand editieren — bei Upstream-Änderungen das Sync-Skript erneut laufen lassen.

Enthält ausschließlich die drei Tabellen, die die offene Berechnungsschicht
braucht (est_tarif, steuerjahr_parameter, Bundesländer-Sätze) als reine Dicts.

================================ DATENPRÜFUNG ================================
Verifikationsstatus gegen Primärquellen:

  ✅ 2026  — vollständig gegen Primärquellen verifiziert
            (§32a EStG / gesetze-im-internet, BMF-PAP 2026 (PDF, W1/W2/W3),
             SVBezGrV 2026, §3/§4 SolzG, Landes-KiStG).
  ⚠ 2024 / 2025 ESt-Tarif — NICHT verifiziert, mutmaßlich teils falsch
     (u.a. 2024 grundfreibetrag = 11604 obsolet; final 11784 €). Bewusst
     identisch zum Upstream gehalten (Parität). Projektübergreifende Korrektur:
     g:/code/.mex/notes/2026-06-06-est-tarif-2024-2025-datenintegritaet.md
=============================================================================
"""

from typing import Any

# 1. Einkommensteuer-Tarif (§32a EStG)

EST_TARIF: dict[int, dict[str, Any]] = {
    # ⚠ 2024 NICHT primärquellen-verifiziert (siehe DATENPRÜFUNG oben).
    2024: {
        "jahr": 2024,
        "grundfreibetrag": 11604,
        "zone2_bis": 17005,
        "zone3_bis": 66760,
        "zone4_bis": 277825,
        "zone2_a": 922.98,
        "zone2_b": 1400.0,
        "zone3_a": 181.19,
        "zone3_b": 2397.0,
        "zone3_c": 991.21,
        "zone4_satz": 0.42,
        "zone4_abzug": 10602.13,
        "zone5_satz": 0.45,
        "zone5_abzug": 18936.88,
    },
    # ⚠ 2025 NICHT primärquellen-verifiziert (siehe DATENPRÜFUNG oben).
    2025: {
        "jahr": 2025,
        "grundfreibetrag": 12096,
        "zone2_bis": 17443,
        "zone3_bis": 68480,
        "zone4_bis": 277825,
        "zone2_a": 954.8,
        "zone2_b": 1400.0,
        "zone3_a": 181.19,
        "zone3_b": 2397.0,
        "zone3_c": 1015.13,
        "zone4_satz": 0.42,
        "zone4_abzug": 10394.14,
        "zone5_satz": 0.45,
        "zone5_abzug": 18728.14,
    },
    # ✅ 2026 gegen §32a EStG (gesetze-im-internet, konsolidiert) verifiziert.
    2026: {
        "jahr": 2026,
        "grundfreibetrag": 12348,
        "zone2_bis": 17799,
        "zone3_bis": 69878,
        "zone4_bis": 277825,
        "zone2_a": 914.51,
        "zone2_b": 1400.0,
        "zone3_a": 173.1,
        "zone3_b": 2397.0,
        "zone3_c": 1034.87,
        "zone4_satz": 0.42,
        "zone4_abzug": 11135.63,
        "zone5_satz": 0.45,
        "zone5_abzug": 19470.38,
    },
}


# 2. Steuerjahr-Parameter (SV-Sätze, Bemessungsgrenzen, Pauschbeträge)

STEUERJAHR_PARAMETER: dict[int, dict[str, Any]] = {
    2024: {
        "jahr": 2024,
        "bbg_kv_pv_monat": 5175.0,
        "bbg_rv_av_monat": 7550.0,
        "kv_an_basis": 7.3,
        "kv_zusatzbeitrag": 1.7,
        "pv_an_basis": 1.7,
        "pv_kinderlos_zuschlag": 0.6,
        "pv_kind_abschlag": 0.25,
        "rv_an": 9.3,
        "av_an": 1.3,
        "kv_ag_basis": 7.3,
        "kv_ag_zusatz_anteil": 0.5,
        "rv_ag": 9.3,
        "av_ag": 1.3,
        "ag_umlage_satz": 1.6,
        "minijob_grenze": 538.0,
        "midijob_obergrenze": 2000.0,
        "mindestlohn": 12.41,
        "anp": 1230.0,
        "sap": 36.0,
        "efa": 4260.0,
        "kfb_voll": 9312.0,
        "kfb_halb": 4656.0,
        "vspmax_sk1": 1900.0,
        "vspmax_sk3": 3000.0,
        "soli_freigrenze_einzel": 18130.0,
        "soli_freigrenze_zusammen": 36260.0,
        "w1stkl5": 12485.0,
        "w2stkl5": 31009.0,
        "w3stkl5": 197034.0,
    },
    2025: {
        "jahr": 2025,
        "bbg_kv_pv_monat": 5512.5,
        "bbg_rv_av_monat": 8050.0,
        "kv_an_basis": 7.3,
        "kv_zusatzbeitrag": 2.5,
        "pv_an_basis": 1.8,
        "pv_kinderlos_zuschlag": 0.6,
        "pv_kind_abschlag": 0.25,
        "rv_an": 9.3,
        "av_an": 1.3,
        "kv_ag_basis": 7.3,
        "kv_ag_zusatz_anteil": 0.5,
        "rv_ag": 9.3,
        "av_ag": 1.3,
        "ag_umlage_satz": 1.59,
        "minijob_grenze": 556.0,
        "midijob_obergrenze": 2000.0,
        "mindestlohn": 12.82,
        "anp": 1230.0,
        "sap": 36.0,
        "efa": 4260.0,
        "kfb_voll": 9600.0,
        "kfb_halb": 4800.0,
        "vspmax_sk1": 1900.0,
        "vspmax_sk3": 3000.0,
        "soli_freigrenze_einzel": 19950.0,
        "soli_freigrenze_zusammen": 39900.0,
        "w1stkl5": 13498.0,
        "w2stkl5": 33533.0,
        "w3stkl5": 213210.0,
    },
    2026: {
        "jahr": 2026,
        "bbg_kv_pv_monat": 5812.5,
        "bbg_rv_av_monat": 8450.0,
        "kv_an_basis": 7.3,
        "kv_zusatzbeitrag": 2.9,
        "pv_an_basis": 1.8,
        "pv_kinderlos_zuschlag": 0.6,
        "pv_kind_abschlag": 0.25,
        "rv_an": 9.3,
        "av_an": 1.3,
        "kv_ag_basis": 7.3,
        "kv_ag_zusatz_anteil": 0.5,
        "rv_ag": 9.3,
        "av_ag": 1.3,
        "ag_umlage_satz": 1.59,
        "minijob_grenze": 603.0,
        "midijob_obergrenze": 2000.0,
        "mindestlohn": 13.9,
        "anp": 1230.0,
        "sap": 36.0,
        "efa": 4260.0,
        "kfb_voll": 9756.0,
        "kfb_halb": 4878.0,
        "vspmax_sk1": 1900.0,
        "vspmax_sk3": 3000.0,
        "soli_freigrenze_einzel": 20350.0,
        "soli_freigrenze_zusammen": 40700.0,
        "w1stkl5": 14071.0,
        "w2stkl5": 34939.0,
        "w3stkl5": 222260.0,
    },
}


# 3. Bundesländer — nur Kirchensteuer- und Pflegeversicherungssätze

BUNDESLAENDER_DATA: dict[str, dict[str, float]] = {
    "Baden-Württemberg": {"kirchensteuersatz": 8.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Bayern": {"kirchensteuersatz": 8.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Berlin": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Brandenburg": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Bremen": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Hamburg": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Hessen": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Mecklenburg-Vorpommern": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Niedersachsen": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Nordrhein-Westfalen": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Rheinland-Pfalz": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Saarland": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Sachsen": {"kirchensteuersatz": 9.0, "pv_an_basis": 2.3, "pv_ag": 1.3},
    "Sachsen-Anhalt": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Schleswig-Holstein": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
    "Thüringen": {"kirchensteuersatz": 9.0, "pv_an_basis": 1.8, "pv_ag": 1.8},
}


def get_est_tarif(jahr: int) -> dict[str, Any]:
    """Gibt die ESt-Tarif-Koeffizienten für ein Jahr zurück."""
    if jahr not in EST_TARIF:
        raise KeyError(f"ESt-Tarif fuer {jahr} nicht vorhanden")
    return EST_TARIF[jahr]


def get_steuerjahr_parameter(jahr: int) -> dict[str, Any]:
    """Gibt alle Parameter für ein Steuerjahr zurück."""
    if jahr not in STEUERJAHR_PARAMETER:
        raise KeyError(f"Steuerjahr {jahr} nicht vorhanden")
    return STEUERJAHR_PARAMETER[jahr]


def get_alle_bundeslaender() -> tuple[str, ...]:
    """Gibt alle 16 Bundesländer-Namen zurück (sortiert)."""
    return tuple(sorted(BUNDESLAENDER_DATA.keys()))


def get_kirchensteuersatz(bundesland: str) -> float:
    """Kirchensteuersatz in Prozent (8.0 oder 9.0)."""
    return float(BUNDESLAENDER_DATA[bundesland]["kirchensteuersatz"])


def get_pv_an_basis(bundesland: str) -> float:
    """PV-AN-Basis-Beitragssatz in Prozent (1.8, Sachsen: 2.3)."""
    return float(BUNDESLAENDER_DATA[bundesland]["pv_an_basis"])


def get_pv_ag(bundesland: str) -> float:
    """PV-AG-Beitragssatz in Prozent (1.8, Sachsen: 1.3)."""
    return float(BUNDESLAENDER_DATA[bundesland]["pv_ag"])
