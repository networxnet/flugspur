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
import laerm

DATA_DIR = os.environ.get("TRACKER_DATA_DIR", "/data")
_P = profil.lade()
LOW_FT = _P["low_ft"]
WOCHENTAG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
             "Freitag", "Samstag", "Sonntag"]


KLEIN = {"P1.0", "P1.1", "P1.2", "P1.3", "?"}


def laden(nur_tief=False, nur_klein=False, umkreis_km=None):
    """Zaehlt Luftfahrzeuge je Wochentag und Stunde.

    Bewusst ohne alles im Speicher zu halten: Bei mehreren Wochen
    Aufzeichnung waeren das Millionen Eintraege. Gezaehlt wird direkt
    beim Lesen, und jede Datei wird gemeldet -- sonst sieht ein langer
    Durchlauf aus wie ein Haenger.
    """
    je_slot = defaultdict(set)
    tage_je_wt = defaultdict(set)
    tage = set()
    t_min = t_max = None
    gelesen = 0
    dateien = sorted(glob.glob(os.path.join(DATA_DIR, "*.ndjson")))
    if not dateien:
        return None
    print(f"{len(dateien)} Datei(en) werden gelesen:", flush=True)
    for pfad in dateien:
        mb = os.path.getsize(pfad) / 1e6
        print(f"   {os.path.basename(pfad):28s} {mb:6.1f} MB ...",
              end="", flush=True)
        n = 0
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
                    t, kid, hoehe = r.get("ts"), r.get("id"), r.get("alt_ft")
                else:
                    t, kid, hoehe = r.get("t"), r.get("icao"), r.get("alt_ft")
                if not t or not kid:
                    continue
                if nur_tief and (hoehe is None or hoehe > LOW_FT):
                    continue
                if nur_klein:
                    g = laerm.gruppe(r.get("type") or r.get("typ"),
                                     r.get("desc"))
                    if g not in KLEIN:
                        continue
                if umkreis_km is not None:
                    la, lo = r.get("lat"), r.get("lon")
                    if la is None or lo is None:
                        continue
                    if profil.hav_km(_P["lat"], _P["lon"], la, lo) > umkreis_km:
                        continue
                t = float(t)
                t_min = t if t_min is None else min(t_min, t)
                t_max = t if t_max is None else max(t_max, t)
                d = datetime.fromtimestamp(t)
                je_slot[(d.weekday(), d.hour)].add((d.date(), kid))
                tage_je_wt[d.weekday()].add(d.date())
                tage.add(d.date())
                n += 1
                gelesen += 1
        print(f" {n} verwertet", flush=True)
    return {"je_slot": je_slot, "tage_je_wt": tage_je_wt, "tage": tage,
            "t_min": t_min, "t_max": t_max, "gelesen": gelesen}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fenster", type=int, default=30,
                    help="Laenge der Beobachtung in Minuten (Standard 30)")
    ap.add_argument("--tief", action="store_true",
                    help="nur tiefe Bewegungen zaehlen (Platzrundenverdacht)")
    ap.add_argument("--alle-muster", action="store_true",
                    help="auch Verkehrsmaschinen zaehlen. Ohne diesen "
                         "Schalter werden nur Kleinflugzeuge, Ultraleicht "
                         "und Motorsegler beruecksichtigt -- der Verkehr, "
                         "um den es an einem Landeplatz geht.")
    ap.add_argument("--umkreis-km", type=float, default=7.0,
                    help="nur Meldungen innerhalb dieses Umkreises um den "
                         "Platz (Vorgabe 7 km; 0 = ohne Begrenzung)")
    a = ap.parse_args()

    erg = laden(nur_tief=a.tief, nur_klein=not a.alle_muster,
                umkreis_km=(a.umkreis_km or None))
    if not erg or not erg["gelesen"]:
        print(f"Keine verwertbaren Daten in {DATA_DIR}.")
        return
    je_slot = erg["je_slot"]
    tage_je_wt = erg["tage_je_wt"]
    print(f"\nDatengrundlage: {erg['gelesen']} Meldungen, "
          f"{len(erg['tage'])} Kalendertage")
    print(f"  von {datetime.fromtimestamp(erg['t_min']):%d.%m.%Y} "
          f"bis {datetime.fromtimestamp(erg['t_max']):%d.%m.%Y}")
    if a.tief:
        print(f"  nur Bewegungen bis {LOW_FT:.0f} ft")
    if not a.alle_muster:
        print("  nur Kleinflugzeuge, Ultraleicht und Motorsegler "
              "(ohne Verkehrsmaschinen)")
    if a.umkreis_km:
        print(f"  nur im Umkreis von {a.umkreis_km:.0f} km um den Platz")

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
        print(f"  Erwartet werden etwa {wert:.0f} verschiedene Luftfahrzeuge "
              f"in {breite*60} Minuten.")
        print("  Gezaehlt werden verschiedene Maschinen, nicht Durchgaenge --")
        print("  eine Maschine in der Platzrunde kommt mehrfach vorbei.")
        if wert < 8:
            noetig = max(2, int(round(12.0 / max(wert, 0.5))))
            print(f"\n  ACHTUNG: Das ist wenig fuer einen Vergleich. Fuer eine")
            print(f"  belastbare Aussage sollten es mindestens etwa zehn")
            print(f"  verschiedene Maschinen sein -- rechnen Sie mit rund")
            print(f"  {noetig} Stunden, oder verteilen Sie die Zaehlung auf")
            print(f"  mehrere Termine zur selben Zeit.")
        elif wert < 20:
            print("\n  Das reicht fuer eine erste Abschaetzung. Eine zweite")
            print("  Zaehlung an einem anderen Tag macht sie belastbarer.")

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
