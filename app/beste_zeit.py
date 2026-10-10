#!/usr/bin/env python3
"""Wann lohnt sich die Zaehlung vor Ort am meisten?

Zweck: Der Testplan sieht vor, den Flugbetrieb eine Weile von Hand
mitzuzaehlen und mit der automatischen Erfassung zu vergleichen. Das ist
die einzige echte Kontrolle unserer Erfassungsquote -- und der Grund,
warum wir ueberhaupt sagen duerfen, wie weit unsere Zahlen Untergrenzen
sind.

Vor Ort stehen kostet Zeit. Dieses Werkzeug sucht aus den bereits
aufgezeichneten Daten den Zeitabschnitt heraus, in dem **am meisten
passiert** -- dann reicht eine kurze Beobachtung fuer eine belastbare
Stichprobe.

Aufruf:   python3 /app/beste_zeit.py
          python3 /app/beste_zeit.py --fenster 60
"""

import argparse
import glob
import json
import os
from collections import defaultdict
from datetime import datetime

import profil

DATA_DIR = os.environ.get("TRACKER_DATA_DIR", "/data")
_P = profil.lade()
LOW_FT = _P["low_ft"]
WOCHENTAG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
             "Freitag", "Samstag", "Sonntag"]


def laden():
    """Alle Positionsmeldungen mit Zeit, Kennung und Hoehe."""
    pts = []
    for pfad in sorted(glob.glob(os.path.join(DATA_DIR, "*.ndjson"))):
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    r = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                if r.get("net") == "OGN":
                    t, kid, alt = r.get("ts"), r.get("id"), r.get("alt_ft")
                else:
                    t, kid, alt = r.get("t"), r.get("icao"), r.get("alt_ft")
                if t and kid:
                    pts.append((float(t), kid, alt))
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fenster", type=int, default=30,
                    help="Laenge der Beobachtung in Minuten (Standard 30)")
    ap.add_argument("--tief", action="store_true",
                    help="nur tiefe Bewegungen zaehlen (Platzrundenverdacht)")
    a = ap.parse_args()

    pts = laden()
    if not pts:
        print(f"Keine Daten in {DATA_DIR}. Erst ein paar Tage mitschneiden.")
        return
    if a.tief:
        pts = [p for p in pts if p[2] is not None and p[2] <= LOW_FT]

    tage = {datetime.fromtimestamp(t).date() for t, _, _ in pts}
    t0 = min(p[0] for p in pts)
    t1 = max(p[0] for p in pts)
    print(f"Datengrundlage: {len(pts)} Positionsmeldungen, "
          f"{len(tage)} Kalendertage")
    print(f"  von {datetime.fromtimestamp(t0):%d.%m.%Y} "
          f"bis {datetime.fromtimestamp(t1):%d.%m.%Y}")
    if a.tief:
        print(f"  nur Bewegungen bis {LOW_FT:.0f} ft")

    # Luftfahrzeuge je (Wochentag, Stunde); ein Luftfahrzeug je Stunde
    # nur einmal, sonst gewinnt ein einziger langer Schulflug.
    je_slot = defaultdict(set)
    tage_je_wt = defaultdict(set)
    for t, kid, _ in pts:
        d = datetime.fromtimestamp(t)
        je_slot[(d.weekday(), d.hour)].add((d.date(), kid))
        tage_je_wt[d.weekday()].add(d.date())

    print(f"\nLuftfahrzeuge je Stunde, Mittel ueber die erfassten Tage")
    print(f"  (leer = nichts erfasst)\n")
    stunden = sorted({h for _, h in je_slot})
    if not stunden:
        return
    kopf = "        " + "".join(f"{h:5d}" for h in stunden)
    print(kopf)
    mittel = {}
    for wt in range(7):
        n_tage = len(tage_je_wt.get(wt, ()))
        if not n_tage:
            continue
        zeile = f"  {WOCHENTAG[wt][:3]}   "
        for h in stunden:
            v = len(je_slot.get((wt, h), ())) / n_tage
            mittel[(wt, h)] = v
            zeile += f"{v:5.1f}" if v else "    ."
        print(zeile + f"   ({n_tage} Tag(e))")

    # Bestes zusammenhaengendes Fenster
    breite = max(1, round(a.fenster / 60))
    beste = []
    for (wt, h), _ in mittel.items():
        fenster = [mittel.get((wt, h + k), 0.0) for k in range(breite)]
        if all((wt, h + k) in mittel for k in range(breite)):
            beste.append((sum(fenster), wt, h))
    beste.sort(reverse=True)

    print(f"\nBeste Zeitfenster von {breite} Stunde(n) "
          f"(erwartete Luftfahrzeuge):\n")
    for wert, wt, h in beste[:5]:
        print(f"  {WOCHENTAG[wt]:11s} {h:02d}:00 bis {h+breite:02d}:00 Uhr   "
              f"etwa {wert:.0f} Luftfahrzeuge")

    if beste:
        wert, wt, h = beste[0]
        print(f"\nEmpfehlung: {WOCHENTAG[wt]}, {h:02d}:00 bis "
              f"{h+breite:02d}:00 Uhr.")
        print(f"  Dann sind etwa {wert:.0f} Luftfahrzeuge zu erwarten -- "
              f"genug fuer eine\n  aussagekraeftige Stichprobe in "
              f"{breite*60} Minuten.")

    print("""
Vor dem Termin beachten:

  * Nur bei Sichtflugwetter zaehlen. Bei niedriger Wolkenuntergrenze
    faellt der Schulbetrieb aus, und die Stichprobe ist wertlos.
    Vorher METAR/TAF fuer EDLN pruefen.
  * Standort so waehlen, dass die Platzrunde einsehbar ist, nicht der
    Flugplatz selbst -- gezaehlt werden soll, was ueber den Ort fliegt.
  * Notieren: Uhrzeit auf die Minute, Richtung, geschaetzte Hoehe,
    Kennzeichen falls lesbar, Muster grob (Hoch- oder Tiefdecker,
    ein- oder zweimotorig, Hubschrauber).
  * Die Uhr vorher mit der des Rechners abgleichen, sonst laesst sich
    nicht zuordnen.
  * Danach: dieselbe halbe Stunde aus der Aufzeichnung auswerten und
    Stueck fuer Stueck vergleichen. Die Differenz ist die
    Erfassungsluecke -- die Zahl, die unsere Auswertungen ehrlich macht.
""")


if __name__ == "__main__":
    main()
