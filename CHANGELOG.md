# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung folgt [CalVer](https://calver.org/) (`JAHR.MINOR`, am Steuerjahr orientiert).

## [Unreleased]

### Added
- Erste Veröffentlichung: Lohnsteuer nach BMF-Programmablaufplan 2026
  (`berechne_lohnsteuer_pap`, `berechne_zve`).
- Einkommensteuer-Tarif nach §32a EStG inkl. Splitting, Solidaritätszuschlag
  und Kirchensteuer (`berechne_einkommensteuer_tarif`, `einkommensteuer`,
  `einkommensteuer_splitting`, `solidaritaetszuschlag`, `kirchensteuer`).
- Steuerjahre 2024, 2025 und 2026.
- Offline, zero dependencies, vollständig typisiert (PEP 561 `py.typed`).
- Python 3.10 – 3.14 unterstützt (`requires-python = ">=3.10"`); CI-Matrix testet
  alle fünf Versionen auf Linux, Windows und macOS.
