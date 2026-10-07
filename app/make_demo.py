#!/usr/bin/env python3
"""Erzeugt einen SIMULIERTEN Mitschnitt, um das Layout der Auswertung zu pruefen.

Die Daten sind frei erfunden. Nur zur Ansicht, niemals als Beleg verwenden.
Aufruf:  EDLN_DATA_DIR=/tmp/demo python3 make_demo.py
"""
import json, math, os, random, time
from datetime import datetime, timedelta

import profil
_P = profil.lade()
LAT, LON = _P["lat"], _P["lon"]
RWY_HDG = (_P["runways"][0]["heading"] if _P["runways"] else 135)
OUT = profil._env("DATA_DIR") or "/tmp/demo"
os.makedirs(OUT, exist_ok=True)
random.seed(7)
KM_LAT, KM_LON = 111.32, 111.32 * math.cos(math.radians(LAT))

MUSTER = [("PIPER PA-28-140/150/160/180", 18), ("CESSNA 172 Skyhawk", 14),
          ("REMOS Mirage", 5), ("ROTORSPORT MTOSport", 4),
          ("GUIMBAL G-2 Cabri", 3), ("CIRRUS SR-22", 3),
          ("ZENAIR CH-600 Zodiac", 2), ("CESSNA 525 CitationJet", 2)]

def offs(dx_km, dy_km):
    return LAT + dy_km / KM_LAT, LON + dx_km / KM_LON

def platzrunde(nord, phase):
    """Ovale Platzrunde entlang des Pistenkurses. nord=True -> Nordseite."""
    a = math.radians(RWY_HDG)
    # Ellipse im Pistenkoordinatensystem: laengs 4.5 km, quer 1.6 km, versetzt
    u = 4.6 * math.cos(phase)
    vv = 1.5 * math.sin(phase) + (1.7 if nord else -1.7)
    dx = u * math.sin(a) + vv * math.cos(a)
    dy = u * math.cos(a) - vv * math.sin(a)
    return offs(dx, dy)

day = datetime.now().strftime("%Y-%m-%d")
base = datetime.strptime(day + " 09:00", "%Y-%m-%d %H:%M").timestamp()
recs = []
ac_id = 0
# Tagesgang: wenig morgens, Spitze nachmittags
for hour in range(9, 19):
    n = [2, 3, 4, 3, 5, 6, 6, 5, 4, 2][hour - 9]
    for _ in range(n):
        ac_id += 1
        hexid = f"3c{ac_id:04x}"
        typ = random.choices([m for m, _ in MUSTER], [w for _, w in MUSTER])[0]
        nord = random.random() < 0.62          # Uebergewicht Nordseite
        runden = random.randint(2, 7)
        t = base + (hour - 9) * 3600 + random.uniform(0, 3000)
        drift = random.uniform(-0.45, 0.75)    # Spurabweichung nach aussen
        alt_base = random.choice([1100, 1200, 1200, 1300, 950])
        for r in range(runden):
            for k in range(90):
                ph = 2 * math.pi * k / 90
                la, lo = platzrunde(nord, ph)
                # Abweichung radial nach aussen
                la += drift * 0.010 * (1 if nord else -1)
                lo += drift * 0.013
                alt = alt_base + 110 * math.sin(ph) + random.uniform(-45, 45)
                recs.append({"t": round(t, 1),
                    "iso": datetime.fromtimestamp(t).isoformat(timespec="seconds"),
                    "icao": hexid, "call": None, "reg": None, "type": None,
                    "desc": typ, "lat": round(la, 5), "lon": round(lo, 5),
                    "alt_ft": round(alt), "gs_kt": 85.0,
                    "track": (math.degrees(ph) + 45) % 360, "vs_fpm": None,
                    "sq": None, "dist_km": 0.0, "mlat": False,
                    "src": "DEMO", "site": _P["code"]})
                t += 4
            t += random.uniform(20, 90)

with open(os.path.join(OUT, f"adsb_{day}.ndjson"), "w") as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"SIMULIERT: {len(recs)} Positionen, {ac_id} Luftfahrzeuge -> {OUT}/adsb_{day}.ndjson")
