"""Top-Query-Beispiel: Lohnsteuer für Steuerklasse 1, 5.000 €/Monat, 2026.

Ausführen mit:  python examples/lohnsteuer_quickstart.py
"""

from lohnsteuer_bmf import berechne_lohnsteuer_pap

ergebnis = berechne_lohnsteuer_pap(
    brutto_jahr=60_000.0,  # 5.000 € * 12
    steuerklasse=1,
    bundesland="Nordrhein-Westfalen",
    mit_kirchensteuer=False,
    kinder=0,
    geburtsjahr=1990,
    kv_zusatzbeitrag=2.9,  # durchschnittlicher Zusatzbeitrag 2026
    ist_sachsen=False,
    jahr=2026,
)

print("Lohnsteuer 2026 — Steuerklasse 1, 5.000 €/Monat brutto")
print(f"  Lohnsteuer/Monat:    {ergebnis['lohnsteuer_monat']:>10.2f} €")
print(f"  Soli/Monat:          {ergebnis['soli_monat']:>10.2f} €")
print(f"  Kirchensteuer/Monat: {ergebnis['kirchensteuer_monat']:>10.2f} €")
print(f"  zvE/Jahr:            {ergebnis['zve_jahr']:>10.2f} €")
print(f"  Vorsorgepauschale:   {ergebnis['vorsorgepauschale']:>10.2f} €")
