#!/usr/bin/env python3
"""Sucht verdaechtige Streckenstuecke in den aufgezeichneten Flugspuren.

Anlass: In der Karte koennen gerade Linien quer ueber das Bild auftauchen.
Dafuer gibt es drei moegliche Ursachen, und sie sehen alle gleich aus:

  1. Echter Flug. Eine Maschine ist tatsaechlich geradeaus geflogen.
  2. Empfangsluecke. Zwischen zwei Meldungen fehlen Positionen; die Karte
     verbindet sie mit einer Geraden, obwohl die Maschine einen Bogen
     geflogen ist.
  3. Verwechslung. Zwei verschiedene Maschinen tragen dieselbe Kennung,
     etwa weil ein Hexcode fehlt oder doppelt vergeben ist.

Unterscheiden lassen sie sich ueber die Geschwindigkeit, die ein
Streckenstueck voraussetzt, und ueber den Vergleich mit der gemeldeten
Geschwindigkeit.

Aufruf:   python3 /app/spuren_pruefen.py
          python3 /app/spuren_pruefen.py --tag 2026-10-09
"""

import argparse
import glob
import json
import math
import os
from collections import defaultdict
from datetime import datetime

import profil

DATA_DIR = os.environ.get("TRACKER_DATA_DIR", "/data")
_P = profil.lade()
hav_km = profil.hav_km

LUECKE_S = 120.0      # wie in visualize.py
MAX_KMH = 800.0       # wie in visualize.py


def laden(tag=None):
    muster = f"*_{tag}.ndjson" if tag else "*.ndjson"
    pts = []
    for pfad in sorted(glob.glob(os.path.join(DATA_DIR, muster))):
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for z in f:
                z = z.strip()
                if not z:
                    continue
                try:
                    r = json.loads(z)
                except json.JSONDecodeError:
                    continue
                if r.get("net") == "OGN":
                    pts.append({"t": r.get("ts"), "id": r.get("id"),
                                "lat": r.get("lat"), "lon": r.get("lon"),
                                "alt": r.get("alt_ft"), "kt": r.get("kt"),
                                "q": "OGN", "typ": r.get("typ")})
                else:
                    pts.append({"t": r.get("t"), "id": r.get("icao"),
                                "lat": r.get("lat"), "lon": r.get("lon"),
                                "alt": r.get("alt_ft"), "kt": r.get("gs_kt"),
                                "q": "ADSB", "typ": r.get("type")})
    return [p for p in pts
            if p["t"] and p["id"] and p["lat"] is not None
            and p["lon"] is not None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="YYYY-MM-DD, sonst alle Tage")
    ap.add_argument("--ab-km", type=float, default=3.0,
                    help="ab welcher Stuecklaenge berichtet wird (km)")
    ap.add_argument("--zeilen", type=int, default=25)
    a = ap.parse_args()

    pts = laden(a.tag)
    if not pts:
        print(f"Keine Daten in {DATA_DIR}.")
        return
    pts.sort(key=lambda p: p["t"])
    nach_ac = defaultdict(list)
    for p in pts:
        nach_ac[p["id"]].append(p)

    print(f"{len(pts)} Meldungen, {len(nach_ac)} Kennungen\n")

    verdacht = []
    luecken = 0
    for acid, tr in nach_ac.items():
        for i in range(1, len(tr)):
            v, p = tr[i - 1], tr[i]
            dt = p["t"] - v["t"]
            if dt <= 0:
                continue
            km = hav_km(v["lat"], v["lon"], p["lat"], p["lon"])
            if dt > LUECKE_S:
                luecken += 1
                continue                      # wird ohnehin getrennt
            if km < a.ab_km:
                continue
            kmh = km / (dt / 3600.0)
            gemeldet = max((x for x in (v.get("kt"), p.get("kt")) if x),
                           default=None)
            verdacht.append((kmh, km, dt, acid, v, p, gemeldet))

    verdacht.sort(reverse=True)
    print(f"{luecken} Pausen ueber {LUECKE_S:.0f} s -- dort trennt die Karte "
          f"die Spur ohnehin.\n")
    if not verdacht:
        print(f"Keine Streckenstuecke ueber {a.ab_km:.0f} km innerhalb von "
              f"{LUECKE_S:.0f} s gefunden.")
        print("Die geraden Linien in der Karte sind dann echte Flugwege.")
        return

    print(f"Streckenstuecke ueber {a.ab_km:.0f} km ohne Unterbrechung, "
          f"nach vorausgesetzter Geschwindigkeit:\n")
    print(f"  {'km/h':>6s} {'km':>6s} {'s':>5s}  {'Kennung':10s} "
          f"{'gemeldet':>9s}  {'Hoehe':>6s}  Uhrzeit   Bewertung")
    for kmh, km, dt, acid, v, p, gemeldet in verdacht[:a.zeilen]:
        if kmh > MAX_KMH:
            bew = "WIRD GETRENNT (unmoeglich)"
        elif gemeldet and kmh > gemeldet * 1.852 * 1.6:
            bew = "verdaechtig (viel schneller als gemeldet)"
        elif dt > 30:
            bew = "Empfangsluecke, Linie geglaettet"
        else:
            bew = "plausibel"
        uhr = datetime.fromtimestamp(v["t"]).strftime("%H:%M:%S")
        g = f"{gemeldet*1.852:.0f}" if gemeldet else "-"
        h = f"{v['alt']:.0f}" if v.get("alt") is not None else "-"
        print(f"  {kmh:6.0f} {km:6.1f} {dt:5.0f}  {str(acid)[:10]:10s} "
              f"{g:>9s}  {h:>6s}  {uhr}  {bew}")

    unmoeglich = sum(1 for x in verdacht if x[0] > MAX_KMH)
    print(f"\n{unmoeglich} Stueck(e) ueber {MAX_KMH:.0f} km/h. "
          f"Diese trennt die Karte seit Oktober 2026 automatisch.")
    print("Bleiben danach noch lange Geraden sichtbar, sind es entweder")
    print("echte Direktfluege oder Empfangsluecken -- keine Fehler.")


if __name__ == "__main__":
    main()
