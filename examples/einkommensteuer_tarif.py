"""Beispiel: Einkommensteuer-Tarif (§32a EStG) für verschiedene zvE, 2026.

Ausführen mit:  python examples/einkommensteuer_tarif.py
"""

from lohnsteuer_bmf import berechne_einkommensteuer_tarif

print("Einkommensteuer-Tarif 2026 (Grundtarif)")
print(f"{'zvE':>10} {'ESt':>10} {'Grenz-%':>9} {'Durchschn-%':>12}  Zone")
for zve in (15_000, 30_000, 50_000, 70_000, 100_000, 300_000):
    t = berechne_einkommensteuer_tarif(zve=zve, jahr=2026)
    print(
        f"{zve:>10,} "
        f"{t['einkommensteuer']:>10,.0f} "
        f"{t['grenzsteuersatz']:>8.2f}% "
        f"{t['durchschnittssteuersatz']:>11.2f}%  "
        f"{t['tarifzone']['name']}"
    )

print()
print("Mit Ehegattensplitting (zvE = gemeinsames Einkommen):")
einzel = berechne_einkommensteuer_tarif(80_000, zusammenveranlagung=False, jahr=2026)
splitting = berechne_einkommensteuer_tarif(80_000, zusammenveranlagung=True, jahr=2026)
ersparnis = einzel["einkommensteuer"] - splitting["einkommensteuer"]
print(f"  Einzelveranlagung: {einzel['einkommensteuer']:>10,.0f} €")
print(f"  Splitting:         {splitting['einkommensteuer']:>10,.0f} €")
print(f"  Splitting-Vorteil: {ersparnis:>10,.0f} €")
