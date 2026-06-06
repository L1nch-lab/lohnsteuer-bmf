#!/usr/bin/env python3
"""Sync-Generator: regeneriert die Datenschicht aus rechner-hub-api (SSoT).

Die Single Source of Truth ist `rechner-hub-api/steuerlogik` (Werte in
`steuerlogik/data/rechner.db`). Dieses Paket wird NIE von Hand gepflegt — die
drei Tabellen, die die offene Schicht braucht, werden mit diesem Skript aus der
DB nach `src/lohnsteuer_bmf/_data.py` regeneriert.

Was dieses Skript automatisiert:
    * `_data.py` — est_tarif (alle Jahre), steuerjahr_parameter (alle Jahre),
      Bundesländer (Kirchensteuer-/PV-Sätze) — deterministisch aus rechner.db.

Was bewusst MANUELL bleibt (durch `tests/test_upstream_parity.py` abgesichert):
    * Die vier Code-Module sind ein Carve-out der Upstream-Logik mit
      Import-Rewrites (siehe Mapping unten). Sie werden hier NICHT überschrieben,
      damit kuratierte Docstrings/Kommentare nicht verloren gehen. Drift fängt
      der Parity-Test ab — er bricht, sobald ein Output abweicht.

      Upstream-Modul                → Paket-Modul (Import-Rewrites)
      ------------------------------------------------------------------
      steuerlogik/lohnsteuer_pap.py → lohnsteuer.py
      steuerlogik/einkommensteuer_tarif.py → tarif.py
      steuerlogik/einkommensteuer.py → einkommensteuer.py
      steuerlogik/constants.py + sv_konstanten.py → konstanten.py (gemerged)
      steuerlogik/db.py (Slice)     → _data.py (von diesem Skript generiert)

      Rewrite-Regel: `steuerlogik.constants`  → `lohnsteuer_bmf.konstanten`
                     `steuerlogik.sv_konstanten` → `lohnsteuer_bmf.konstanten`
                     `steuerlogik.einkommensteuer` → `lohnsteuer_bmf.einkommensteuer`
                     `steuerlogik.db import <accessor>` → `lohnsteuer_bmf._data import <accessor>`

Usage:
    python tools/sync_from_upstream.py [--upstream PATH] [--check]

    --check : nichts schreiben; nur prüfen, ob die DB-Werte von der aktuellen
              _data.py abweichen (Werte-Vergleich, exit 1 bei Drift).

Nach einem Schreib-Lauf:  ruff format . && ruff check . && mypy src/ && pytest -q
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PY = REPO_ROOT / "src" / "lohnsteuer_bmf" / "_data.py"

# Felder der Bundesländer-Tabelle, die die offene Schicht nutzt (kein Grunderwerb-
# steuersatz, keine Gemeinde-Hebesätze — die bleiben proprietär im Upstream).
BUNDESLAND_FELDER = ("kirchensteuersatz", "pv_an_basis", "pv_ag")

# Verifikationsstatus-Annotationen je Steuerjahr (kuratiert, siehe Vermerk).
EST_JAHR_KOMMENTAR = {
    2024: "    # ✅ 2024 final (GFB 11.784, BGBl. 2024 I Nr. 386) gegen BMF EStH 2024 verifiziert.",
    2025: "    # ✅ 2025 (StFeG, BGBl. 2024 I Nr. 449) gegen BMF EStH 2025 verifiziert.",
    2026: "    # ✅ 2026 gegen §32a EStG (gesetze-im-internet, konsolidiert) verifiziert.",
}

HEADER = '''"""Inline-Datenschicht für lohnsteuer-bmf (ersetzt den db.py/SQLite-Slice).

GENERIERT von tools/sync_from_upstream.py aus rechner-hub-api/steuerlogik/data/rechner.db.
NICHT von Hand editieren — bei Upstream-Änderungen das Sync-Skript erneut laufen lassen.

Enthält ausschließlich die drei Tabellen, die die offene Berechnungsschicht
braucht (est_tarif, steuerjahr_parameter, Bundesländer-Sätze) als reine Dicts.

================================ DATENPRÜFUNG ================================
Verifikationsstatus gegen Primärquellen:

  ✅ 2024 / 2025 / 2026 ESt-Tarif §32a Abs. 1 — vollständig gegen Primärquellen
            verifiziert (2026-06-07):
              2024 FINAL (GFB 11.784): BGBl. 2024 I Nr. 386 / BMF EStH 2024;
              2025: StFeG (BGBl. 2024 I Nr. 449) / BMF EStH 2025;
              2026: §32a EStG (gesetze-im-internet, konsolidiert).
            Zusätzlich Kontinuitäts-Check an allen Zonengrenzen (Abzugsbeträge
            stimmen auf den Cent mit dem Gesetzestext überein).
  ✅ 2026 SV/PAP — BMF-PAP 2026 (PDF, W1/W2/W3), SVBezGrV 2026, §3/§4 SolzG,
            Landes-KiStG.
  Korrektur-Vorgang 2024/2025-ESt (erledigt 2026-06-07):
     g:/code/.mex/notes/2026-06-06-est-tarif-2024-2025-datenintegritaet.md
=============================================================================
"""

from typing import Any
'''


def _fmt(value: Any) -> str:
    """Formatiert einen Wert als Python-Literal (int bleibt int, float via repr)."""
    if isinstance(value, bool):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return repr(value)


def _read_tables(db_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        est = [dict(r) for r in conn.execute("SELECT * FROM est_tarif ORDER BY jahr")]
        stp = [dict(r) for r in conn.execute("SELECT * FROM steuerjahr_parameter ORDER BY jahr")]
        bl = [
            dict(r)
            for r in conn.execute(
                "SELECT name, kirchensteuersatz, pv_an_basis, pv_ag "
                "FROM bundeslaender ORDER BY name"
            )
        ]
    finally:
        conn.close()
    return est, stp, bl


def _render_year_dict(rows: list[dict], kommentar: dict[int, str] | None = None) -> str:
    out: list[str] = []
    for row in rows:
        jahr = row["jahr"]
        if kommentar and jahr in kommentar:
            out.append(kommentar[jahr])
        out.append(f"    {jahr}: {{")
        for key, val in row.items():
            out.append(f'        "{key}": {_fmt(val)},')
        out.append("    },")
    return "\n".join(out)


def _render_bundeslaender(rows: list[dict]) -> str:
    out: list[str] = []
    for row in rows:
        felder = ", ".join(f'"{f}": {_fmt(row[f])}' for f in BUNDESLAND_FELDER)
        out.append(f"    {_fmt(row['name'])}: {{{felder}}},")
    return "\n".join(out)


ACCESSORS = '''

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
'''


def render_data_py(est: list[dict], stp: list[dict], bl: list[dict]) -> str:
    parts = [
        HEADER,
        "\n# 1. Einkommensteuer-Tarif (§32a EStG)\n",
        "EST_TARIF: dict[int, dict[str, Any]] = {",
        _render_year_dict(est, EST_JAHR_KOMMENTAR),
        "}\n",
        "\n# 2. Steuerjahr-Parameter (SV-Sätze, Bemessungsgrenzen, Pauschbeträge)\n",
        "STEUERJAHR_PARAMETER: dict[int, dict[str, Any]] = {",
        _render_year_dict(stp),
        "}\n",
        "\n# 3. Bundesländer — nur Kirchensteuer- und Pflegeversicherungssätze\n",
        "BUNDESLAENDER_DATA: dict[str, dict[str, float]] = {",
        _render_bundeslaender(bl),
        "}",
        ACCESSORS,
    ]
    return "\n".join(parts) + "\n"


def _find_upstream_db(upstream: Path) -> Path:
    db = upstream / "steuerlogik" / "data" / "rechner.db"
    if not db.is_file():
        sys.exit(f"FEHLER: rechner.db nicht gefunden unter {db}")
    return db


def _check_values(est: list[dict], stp: list[dict], bl: list[dict]) -> int:
    """Vergleicht DB-Werte gegen die aktuelle _data.py (Werte, nicht Bytes)."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from lohnsteuer_bmf import _data  # noqa: PLC0415

    drift: list[str] = []
    db_est = {r["jahr"]: r for r in est}
    if db_est != _data.EST_TARIF:
        drift.append("EST_TARIF weicht von rechner.db ab")
    db_stp = {r["jahr"]: r for r in stp}
    if db_stp != _data.STEUERJAHR_PARAMETER:
        drift.append("STEUERJAHR_PARAMETER weicht von rechner.db ab")
    db_bl = {r["name"]: {f: r[f] for f in BUNDESLAND_FELDER} for r in bl}
    if db_bl != _data.BUNDESLAENDER_DATA:
        drift.append("BUNDESLAENDER_DATA weicht von rechner.db ab")
    if drift:
        print("DRIFT erkannt:")
        for d in drift:
            print(f"  - {d}")
        print("\n-> tools/sync_from_upstream.py ohne --check laufen lassen.")
        return 1
    print("OK: _data.py-Werte stimmen mit rechner.db überein.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--upstream",
        type=Path,
        default=REPO_ROOT.parent / "rechner-hub-api",
        help="Pfad zum rechner-hub-api-Repo (Default: Sibling)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Nur prüfen, ob _data.py von rechner.db abweicht (exit 1 bei Drift).",
    )
    args = ap.parse_args()

    db = _find_upstream_db(args.upstream)
    est, stp, bl = _read_tables(db)

    if args.check:
        return _check_values(est, stp, bl)

    DATA_PY.write_text(render_data_py(est, stp, bl), encoding="utf-8")
    print(f"geschrieben: {DATA_PY}")
    print("Jetzt:  ruff format . && ruff check . && mypy src/ && pytest -q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
