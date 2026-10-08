#!/usr/bin/env python3
"""Tagesauswertung des EDLN-Mitschnitts.

Aufruf:
  python3 summary.py             letzter vorhandener Tag
  python3 summary.py 2026-09-28  bestimmter Tag
  python3 summary.py --all       alle Tage nacheinander
"""
import json, os, sys, math, glob, csv
from collections import defaultdict

import profil, kennzeichen

_P       = profil.lade()
LAT      = _P["lat"]
LON      = _P["lon"]
DATA_DIR = profil._env("DATA_DIR") or "/data"
OVER_KM  = _P["overflight_km"]
LOW_FT   = _P["low_ft"]
RUNWAYS  = _P["runways"]
PLATZRUNDE = _P["platzrunde"]
ORTE     = _P["orte"]
DEBOUNCE = 180
NEAR_KM  = 9.0          # Nahbereich fuer Platzrundenverdacht
MIN_PTS  = 40           # Mindestzahl tiefer Positionen
MIN_MIN  = 8            # Mindestdauer in Minuten


hav_km = profil.hav_km
ang_diff = profil.winkel_diff


def _ogn_id(r):
    """OGN-Kennung auf die ADS-B-Kennung abbilden, damit dieselbe Maschine
    nicht doppelt gezaehlt wird. ICAxxxxxx -> xxxxxx."""
    k = r.get("icao")
    if k:
        return k.lower()
    i = r.get("id") or ""
    if i.startswith("ICA") and len(i) == 9:
        return i[3:].lower()
    return i

_NAMEN = None

def _namen():
    global _NAMEN
    if _NAMEN is None:
        _NAMEN = kennzeichen.Namen(DATA_DIR)
    return _NAMEN

def load_day(day):
    """Liest ADS-B und OGN eines Tages und vereinheitlicht die Felder."""
    pts = []
    N = _namen()
    for path in (os.path.join(DATA_DIR, f"adsb_{day}.ndjson"),
                 os.path.join(DATA_DIR, f"ogn_{day}.ndjson")):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("net") == "OGN":
                    pts.append({
                        "t": r.get("ts"), "id": _ogn_id(r), "lat": r.get("lat"),
                        "lon": r.get("lon"), "alt": r.get("alt_ft"),
                        "trk": r.get("course"),
                        "desc": N.muster(hexid=r.get("icao"), ogn_id=r.get("id"),
                                         desc=r.get("typ")),
                        "kz": N.anzeige(hexid=r.get("icao"), ogn_id=r.get("id"),
                                        reg=r.get("reg")),
                        "net": "OGN",
                    })
                else:
                    N.lerne(r.get("icao"), r.get("reg"),
                            r.get("type"), r.get("desc"))
                    pts.append({
                        "t": r.get("t"), "id": r.get("icao"), "lat": r.get("lat"),
                        "lon": r.get("lon"), "alt": r.get("alt_ft"),
                        "trk": r.get("track"),
                        "desc": r.get("desc") or r.get("type"),
                        "kz": N.anzeige(hexid=r.get("icao"), reg=r.get("reg")),
                        "net": "ADSB",
                    })
    _max = _P["max_alt_ft"]
    pts = [p for p in pts if p["t"] and p["id"] and p["lat"] is not None
           and (p["alt"] is None or p["alt"] <= _max)]
    pts.sort(key=lambda p: p["t"])
    return pts

def report(day):
    pts = load_day(day)
    if not pts:
        print(f"Keine Daten fuer {day}")
        return

    by_ac = defaultdict(list)
    for p in pts:
        by_ac[p["id"]].append(p)

    span_h = (pts[-1]["t"] - pts[0]["t"]) / 3600.0

    print("=" * 66)
    print(f" {_P['code']} -- {_P['name']}")
    print(f" Mitschnitt {day}   Positionen: {len(pts)}   Luftfahrzeuge: {len(by_ac)}")
    print(f" Erfasster Zeitraum: {span_h:.1f} h")
    print("=" * 66)

    # --- Musterspektrum ---
    typen = defaultdict(set)
    for acid, tr in by_ac.items():
        d = next((p["desc"] for p in tr if p["desc"]), None)
        typen[d or "unbekannt"].add(acid)
    print("\nMuster (Anzahl verschiedener Luftfahrzeuge):")
    for name, s in sorted(typen.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(s):3d}  {name}")

    # --- Platzrundenverdacht ---
    verdacht = []
    for acid, tr in (by_ac.items() if PLATZRUNDE else []):
        low = [p for p in tr
               if p["alt"] is not None and p["alt"] <= LOW_FT
               and hav_km(LAT, LON, p["lat"], p["lon"]) <= NEAR_KM]
        if len(low) >= MIN_PTS:
            dur = (low[-1]["t"] - low[0]["t"]) / 60.0
            if dur >= MIN_MIN:
                d = next((p["desc"] for p in tr if p["desc"]), None) or "unbekannt"
                verdacht.append((acid, d, dur, len(low),
                                 min(p["alt"] for p in low)))
    verdacht.sort(key=lambda v: -v[2])
    if PLATZRUNDE:
        print(f"\nPlatzrunden-/Schulflugverdacht ({len(verdacht)} Luftfahrzeuge, "
              f"tief <= {LOW_FT:.0f} ft, >= {MIN_MIN} min im Nahbereich):")
    else:
        print("\nPlatzrundenerkennung fuer diesen Platz deaktiviert "
              "(kein Platzrundenbetrieb).")
    for acid, d, dur, n, minalt in verdacht:
        kz = _namen().anzeige(hexid=acid)
        print(f"  {kz:9s} {acid:7s} {d[:26]:28s} {dur:5.0f} min  "
              f"{n:4d} Pos  min {minalt:.0f} ft")
    if PLATZRUNDE and not verdacht:
        print("  (keiner)")

    # --- Betriebsrichtung ---
    # Parallelbahnen (z. B. 05L/05R) haben denselben Kurs und sind aus der
    # Flugspur NICHT unterscheidbar. Daher wird nach Richtung gruppiert.
    gruppen = {}
    for r in RUNWAYS:
        gruppen.setdefault(round(r["heading"]), []).append(r["id"])
    zaehler = {h: 0 for h in gruppen}
    for p in pts:
        if p["trk"] is None or p["alt"] is None or p["alt"] > LOW_FT:
            continue
        if hav_km(LAT, LON, p["lat"], p["lon"]) > 5:
            continue
        for h in gruppen:
            if ang_diff(p["trk"], h) < 30:
                zaehler[h] += 1
                break
    tot = sum(zaehler.values())
    if tot:
        teile = "  |  ".join(
            f"Richtung {'/'.join(gruppen[h])} {100*v/tot:.0f} %"
            for h, v in zaehler.items())
        print(f"\nBetriebsrichtung (tiefe Ziele auf Pistenkurs): {teile}  (n={tot})")
        if any(len(v) > 1 for v in gruppen.values()):
            print("  Hinweis: Parallelbahnen sind aus der Flugspur nicht "
                  "unterscheidbar, daher zusammengefasst.")
    else:
        print("\nBetriebsrichtung: zu wenig Daten")

    # --- Ueberflugereignisse ---
    print(f"\nUeberflug-Ereignisse je Ortslage "
          f"(Radius {OVER_KM} km, ein Ereignis je Luftfahrzeug und Durchgang).")
    print(f"  'tief' = hoechstens {LOW_FT:.0f} ft, laermrelevant. 'gesamt' = alle "
          f"Hoehen,\n  enthaelt auch hohen Durchgangsverkehr Richtung Duesseldorf.")
    events = defaultdict(list)
    for ortname, ola, olo in ORTE:
        last = {}
        for p in pts:
            if hav_km(ola, olo, p["lat"], p["lon"]) <= OVER_KM:
                prev = last.get(p["id"])
                if prev is None or p["t"] - prev > DEBOUNCE:
                    events[ortname].append(p)
                last[p["id"]] = p["t"]

    rows = []
    for ortname, _, _ in ORTE:
        ev = events.get(ortname, [])
        alts = [e["alt"] for e in ev if e["alt"] is not None]
        tief = sum(1 for a in alts if a <= LOW_FT)
        if alts:
            info = (f"min {min(alts):5.0f} ft   median {sorted(alts)[len(alts)//2]:5.0f} ft"
                    f"   unter 1500 ft: {sum(1 for a in alts if a < 1500)}")
        else:
            info = ""
        print(f"  {ortname:34s} tief {tief:4d}   gesamt {len(ev):4d}   {info}")
        rows.append({
            "tag": day, "ort": ortname, "ereignisse": len(ev),
            "min_ft": min(alts) if alts else "",
            "median_ft": sorted(alts)[len(alts)//2] if alts else "",
            "unter_1500ft": sum(1 for a in alts if a < 1500) if alts else 0,
        })

    out = os.path.join(DATA_DIR, f"report_{day}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV geschrieben: {out}")

    print("\nHinweis: erfasst werden nur Luftfahrzeuge mit ADS-B/MLAT bzw. FLARM.")
    print("Maschinen mit reinem Mode-A/C-Transponder fehlen -> Zahlen sind Untergrenzen.")

def available_days():
    days = set()
    for p in glob.glob(os.path.join(DATA_DIR, "*_????-??-??.ndjson")):
        days.add(os.path.basename(p).rsplit("_", 1)[1][:10])
    return sorted(days)

def main():
    days = available_days()
    if not days:
        print(f"Keine Mitschnittdateien in {DATA_DIR}")
        sys.exit(1)
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "--all":
        for d in days:
            report(d)
            print()
    elif arg:
        report(arg)
    else:
        report(days[-1])

if __name__ == "__main__":
    main()
