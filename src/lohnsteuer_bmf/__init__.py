"""lohnsteuer-bmf — Lohn- und Einkommensteuer nach BMF-Programmablaufplan 2026.

Offline, typisiert, ohne externe Abhängigkeiten. Carve-out der Commodity-Schicht
aus rechner-hub-api/steuerlogik.

Schnellstart (Top-Query: Steuerklasse 1, 5.000 €/Monat brutto, 2026)::

    from lohnsteuer_bmf import berechne_lohnsteuer_pap

    ergebnis = berechne_lohnsteuer_pap(
        brutto_jahr=60_000.0,        # 5.000 € * 12
        steuerklasse=1,
        bundesland="Nordrhein-Westfalen",
        mit_kirchensteuer=False,
        kinder=0,
        geburtsjahr=1990,
        kv_zusatzbeitrag=2.9,        # durchschnittlicher Zusatzbeitrag 2026
        ist_sachsen=False,
        jahr=2026,
    )
    print(ergebnis["lohnsteuer_monat"])

Die breite Abdeckung (~58 weitere Rechner inkl. Sozialleistungen) gibt es als
gehostete REST-API: https://rechner-hub.de/steuerrechner-api/
"""

from lohnsteuer_bmf.einkommensteuer import (
    einkommensteuer,
    einkommensteuer_splitting,
    kirchensteuer,
    solidaritaetszuschlag,
)
from lohnsteuer_bmf.konstanten import (
    AKTUELLES_STEUERJAHR,
    BUNDESLAENDER,
    UNTERSTUETZTE_JAHRE,
)
from lohnsteuer_bmf.lohnsteuer import (
    berechne_lohnsteuer_pap,
    berechne_zve,
)
from lohnsteuer_bmf.tarif import berechne_einkommensteuer_tarif

__version__ = "2026.1"

__all__ = [
    "AKTUELLES_STEUERJAHR",
    "BUNDESLAENDER",
    "UNTERSTUETZTE_JAHRE",
    "__version__",
    "berechne_einkommensteuer_tarif",
    "berechne_lohnsteuer_pap",
    "berechne_zve",
    "einkommensteuer",
    "einkommensteuer_splitting",
    "kirchensteuer",
    "solidaritaetszuschlag",
]
