<div align="center">

<img src="https://raw.githubusercontent.com/L1nch-lab/lohnsteuer-bmf/main/assets/banner.svg" alt="lohnsteuer-bmf" width="100%">

**Lohn- und Einkommensteuer nach dem BMF-Programmablaufplan 2026: offline, typisiert, ohne externe Abhängigkeiten.**

[![PyPI](https://img.shields.io/pypi/v/lohnsteuer-bmf.svg)](https://pypi.org/project/lohnsteuer-bmf/)
[![Python](https://img.shields.io/pypi/pyversions/lohnsteuer-bmf.svg)](https://pypi.org/project/lohnsteuer-bmf/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/L1nch-lab/lohnsteuer-bmf/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[Installation](#installation) · [Schnellstart](#schnellstart) · [API](https://api.rechner-hub.de/steuerrechner-api/) · [PyPI](https://pypi.org/project/lohnsteuer-bmf/)

</div>

# lohnsteuer-bmf

`pip install` und loslegen: kein Code-Generator, kein PAP-XML-Parsing, keine
Laufzeit-Abhängigkeiten. Die Steuerwerte für 2026 sind gegen Primärquellen
verifiziert (§32a EStG, BMF-PAP 2026, SV-Rechengrößenverordnung 2026).

> 🇬🇧 **English speakers:** scroll down for the [English section](#english).

---

## Installation

```bash
pip install lohnsteuer-bmf
```

Python ≥ 3.12. Keine Abhängigkeiten.

## Schnellstart

Die häufigste Frage zuerst — **Steuerklasse 1, 5.000 € brutto/Monat, 2026:**

```python
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

print(ergebnis)
# {'lohnsteuer_monat': 777.33, 'soli_monat': 0.0, 'kirchensteuer_monat': 0.0,
#  'zve_jahr': 46464.0, 'vorsorgepauschale': 12270.0}
```

### Einkommensteuer-Tarif (§32a EStG)

```python
from lohnsteuer_bmf import berechne_einkommensteuer_tarif

t = berechne_einkommensteuer_tarif(zve=50_000, jahr=2026)
print(t["einkommensteuer"], t["grenzsteuersatz"], t["tarifzone"]["name"])
# 10548.0 35.0 'Obere Progressionszone'
```

### Bausteine

```python
from lohnsteuer_bmf import (
    einkommensteuer,             # §32a EStG, Grundtarif
    einkommensteuer_splitting,   # §32a Abs. 5 EStG, Ehegattensplitting
    solidaritaetszuschlag,       # §3/§4 SolzG inkl. Milderungszone
    kirchensteuer,               # 8 % (BY, BW) / 9 % (übrige Länder)
)

einkommensteuer(50_000, 2026)              # 10548
einkommensteuer_splitting(100_000, 2026)   # 21096
solidaritaetszuschlag(30_864, jahr=2026)   # 1251.17
kirchensteuer(10_000, "Bayern")            # 800.0
```

## Was ist drin

| Funktion | Rechtsgrundlage |
|---|---|
| `berechne_lohnsteuer_pap` | BMF-Programmablaufplan 2026 (BMF-Schreiben v. 12.11.2025) |
| `berechne_zve` | zu versteuerndes Einkommen aus Brutto (Vorsorgepauschale etc.) |
| `berechne_einkommensteuer_tarif` | §32a EStG inkl. Grenz-/Durchschnittssteuersatz |
| `einkommensteuer` / `einkommensteuer_splitting` | §32a Abs. 1 / Abs. 5 EStG |
| `solidaritaetszuschlag` | §3/§4 SolzG |
| `kirchensteuer` | Landeskirchensteuergesetze |

Unterstützte Steuerjahre: **2024, 2025, 2026.**

> **Hinweis zu 2024/2025:** Verifiziert und für den produktiven Einsatz empfohlen
> ist das Steuerjahr **2026**; die Werte für 2024/2025 entsprechen dem Upstream-Stand
> und werden noch gegen Primärquellen nachgeprüft.

## Brauchst du mehr als Lohn-/Einkommensteuer?

Dieses Paket ist die offene Commodity-Schicht. Die **breite Abdeckung** — rund 58
weitere deutsche Rechner inkl. Sozialleistungen (Bürgergeld, Wohngeld, Elterngeld,
Gewerbe-/Grunderwerb-/Erbschaftsteuer, Krypto, Photovoltaik u.v.m.), Batch-Endpoints
und Gemeinde-Hebesätze — gibt es als gehostete REST-API:

👉 **[api.rechner-hub.de/steuerrechner-api](https://api.rechner-hub.de/steuerrechner-api/)**

## Genauigkeit & Haftung

Die Berechnungen folgen den offiziellen BMF-Formeln, ersetzen aber **keine
Steuerberatung**. Alle Angaben ohne Gewähr. Das Paket bildet die maschinelle
Lohnsteuer-/ESt-Berechnung ab, nicht jeden Einzelfall des Veranlagungsverfahrens.

## Lizenz

[MIT](LICENSE) © 2026 L1nch-lab

---

## English

**German wage tax (Lohnsteuer) and income tax (Einkommensteuer) per the official
BMF payroll algorithm (Programmablaufplan) 2026 — offline, typed, zero dependencies.**

```bash
pip install lohnsteuer-bmf
```

Quick start — tax class 1, €5,000 gross/month, 2026:

```python
from lohnsteuer_bmf import berechne_lohnsteuer_pap

result = berechne_lohnsteuer_pap(
    brutto_jahr=60_000.0,        # 5,000 EUR * 12
    steuerklasse=1,              # tax class 1
    bundesland="Nordrhein-Westfalen",
    mit_kirchensteuer=False,     # church tax
    kinder=0,                    # children
    geburtsjahr=1990,            # birth year
    kv_zusatzbeitrag=2.9,        # avg. health-insurance surcharge 2026
    ist_sachsen=False,           # Saxony special rule
    jahr=2026,                   # tax year
)
print(result["lohnsteuer_monat"])  # 777.33  (monthly wage tax in EUR)
```

What's included: monthly **Lohnsteuer** (BMF-PAP 2026), the **§32a income-tax tariff**
(incl. spouse splitting, marginal/average rates), **solidarity surcharge** and
**church tax**. Tax years 2024–2026 (2026 verified against primary sources;
2024/2025 mirror upstream and are pending re-verification).

Need the full breadth (≈58 more German calculators incl. social benefits, batch
endpoints, municipal trade-tax rates)? Use the hosted REST API:
**[api.rechner-hub.de/steuerrechner-api](https://api.rechner-hub.de/steuerrechner-api/)**.

Not tax advice — provided as is. Licensed under [MIT](LICENSE).
