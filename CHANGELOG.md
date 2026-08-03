# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung folgt [CalVer](https://calver.org/) (`JAHR.MINOR`, am Steuerjahr orientiert).

## [Unreleased]

## [2026.2] - 2026-08-03

### Fixed

- **Vorsorgepauschale rechnet jetzt mit dem ermäßigten KV-Satz 7,0 %** statt des
  allgemeinen Satzes 7,3 % (§ 39b Abs. 2 Satz 5 Nr. 3 Buchst. b EStG i. V. m.
  § 243 SGB V). Vorher war die Vorsorgepauschale um 0,3 % × min(Brutto, BBG-KV)
  zu hoch und die Lohnsteuer damit systematisch zu niedrig — bis zu ~8 €/Monat
  ab der Beitragsbemessungsgrenze. Verifiziert gegen den offiziellen
  BMF-Steuerrechner. Danke an @Physik42 für die Meldung (#1).

### Added

- `berechne_zve()` akzeptiert einen neuen optionalen Parameter
  `pv_basissatz: bool = False`: erzwingt in der Vorsorgepauschale den
  PV-Basissatz nach § 55 Abs. 1 S. 1 SGB XI (ohne Kinderlosenzuschlag und
  Kinder-Abschläge). Benötigt z. B. für das pauschalierte Nettoentgelt beim
  Kurzarbeitergeld (§ 153 Abs. 1 S. 4 Nr. 3 SGB III). Default unverändert.

## [2026.1] - 2026-06-14

### Changed

- Python 3.10 – 3.14 unterstützt (vorher nur 3.12+); `requires-python = ">=3.10"`.
  Die CI-Matrix testet alle fünf Versionen auf Linux, Windows und macOS.
  Keine Code- oder Berechnungsänderung — reine Kompatibilitätserweiterung.

## [2026.0]

### Added

- Erste Veröffentlichung: Lohnsteuer nach BMF-Programmablaufplan 2026
  (`berechne_lohnsteuer_pap`, `berechne_zve`).
- Einkommensteuer-Tarif nach §32a EStG inkl. Splitting, Solidaritätszuschlag
  und Kirchensteuer (`berechne_einkommensteuer_tarif`, `einkommensteuer`,
  `einkommensteuer_splitting`, `solidaritaetszuschlag`, `kirchensteuer`).
- Steuerjahre 2024, 2025 und 2026.
- Offline, zero dependencies, vollständig typisiert (PEP 561 `py.typed`).
