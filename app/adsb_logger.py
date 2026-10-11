#!/usr/bin/env python3
"""ADS-B/MLAT-Mitschnitt rund um einen Flugplatz. Nur Standardbibliothek.

Fragt offene, authentifizierungsfreie Netze im Takt ab und schreibt jede
Position tagesweise als NDJSON. Bei Ausfall einer Quelle wird auf die naechste
gewechselt, bei Netzproblemen mit exponentiellem Backoff gewartet.
"""
import json, os, sys, time, math, urllib.request, urllib.error
from datetime import datetime, timezone

import profil
import neustart

_P        = profil.lade()
SITE      = _P["code"]
LAT       = _P["lat"]
LON       = _P["lon"]
RADIUS_NM = _P["radius_nm"]
MAX_ALT   = _P["max_alt_ft"]
INTERVAL  = _P["interval_s"]
DATA_DIR  = profil._env("DATA_DIR") or "/data"

UA = "Flugspur/1.0 (Buergerinitiative Fluglaerm; nicht-kommerziell)"

SOURCES = [
    ("adsb.fi",  "https://opendata.adsb.fi/api/v2/lat/{lat:.4f}/lon/{lon:.4f}/dist/{nm:.0f}"),
    ("adsb.lol", "https://api.adsb.lol/v2/lat/{lat:.4f}/lon/{lon:.4f}/dist/{nm:.0f}"),
]

def log(msg):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [adsb] {msg}", flush=True)

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))

def as_float(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        if v.lower() == "ground":
            return 0.0
        try:
            return float(v)
        except ValueError:
            return None
    return None

def normalise(ac, source, now):
    """Vereinheitlicht einen Datensatz. Gibt None zurueck, wenn unbrauchbar."""
    lat = as_float(ac.get("lat"))
    lon = as_float(ac.get("lon"))
    if lat is None or lon is None:
        return None
    dist = haversine_km(LAT, LON, lat, lon)
    if dist > RADIUS_NM * 1.852:
        return None
    alt = as_float(ac.get("alt_baro"))
    if alt is None:
        alt = as_float(ac.get("alt_geom"))
    if alt is not None and alt > MAX_ALT:
        return None
    icao = (ac.get("hex") or ac.get("icao") or "").strip().lower()
    if not icao:
        return None
    rec = {
        "t":     round(now, 1),
        "iso":   datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds"),
        "icao":  icao,
        "call":  (ac.get("flight") or "").strip() or None,
        "reg":   ac.get("r") or None,
        "type":  ac.get("t") or None,
        "desc":  ac.get("desc") or None,
        "lat":   round(lat, 5),
        "lon":   round(lon, 5),
        "alt_ft": alt,
        "gs_kt": as_float(ac.get("gs")),
        "track": as_float(ac.get("track")),
        "vs_fpm": as_float(ac.get("baro_rate")) or as_float(ac.get("geom_rate")),
        "sq":    ac.get("squawk") or None,
        "dist_km": round(dist, 2),
        "mlat":  bool(ac.get("mlat")),
        "src":   source,
        "site":  SITE,
    }
    return rec

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    import kennzeichen
    namen = kennzeichen.Namen(DATA_DIR)
    gelernt_zuletzt = 0
    log(f"Start {SITE} ({_P['name']}) | {LAT},{LON} | {RADIUS_NM} NM | < {MAX_ALT:.0f} ft "
        f"| alle {INTERVAL}s | -> {DATA_DIR}")
    total = 0
    si = 0
    backoff = INTERVAL
    fh, fh_day = None, None
    _START_STAND = neustart.stand()
    try:
        while True:
            cycle_start = time.time()
            neustart.beenden_wenn_neu(_START_STAND)
            name, tmpl = SOURCES[si % len(SOURCES)]
            url = tmpl.format(lat=LAT, lon=LON, nm=RADIUS_NM)
            try:
                data = fetch(url)
                aircraft = data.get("ac") or data.get("aircraft") or []
                now = time.time()
                day = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
                if fh is None or day != fh_day:
                    if fh:
                        fh.close()
                    fh = open(os.path.join(DATA_DIR, f"adsb_{day}.ndjson"), "a", encoding="utf-8")
                    fh_day = day
                n = 0
                for ac in aircraft:
                    rec = normalise(ac, name, now)
                    if rec:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        n += 1
                        if rec.get("reg"):
                            namen.lerne(rec["icao"], rec["reg"],
                                        rec.get("type"), rec.get("desc"))
                fh.flush()
                # Zuordnung Hexcode -> Kennzeichen alle 5 Minuten sichern.
                # Dadurch bleibt sie bekannt, wenn dieselbe Maschine spaeter
                # nur ueber OGN oder ganz ohne Kennzeichenfeld auftaucht.
                if now - gelernt_zuletzt > 300:
                    try:
                        ges = kennzeichen.reg_sichern(DATA_DIR, namen.reg)
                        if gelernt_zuletzt == 0:
                            log(f"Kennzeichen bekannt: {ges}")
                    except Exception as e:
                        log(f"Kennzeichenliste nicht schreibbar: {e}")
                    gelernt_zuletzt = now
                total += n
                with open(os.path.join(DATA_DIR, "_heartbeat_adsb.txt"), "w") as hb:
                    hb.write(f"{int(now)}\n{datetime.now():%Y-%m-%d %H:%M:%S}\n"
                             f"ziele={n}\ngesamt={total}\nquelle={name}\n")
                backoff = INTERVAL
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log(f"Quelle {name} gestoert ({type(e).__name__}: {e}) -> wechsle")
                si += 1
                backoff = min(backoff * 2, 300)
                time.sleep(backoff)
                continue
            sleep = INTERVAL - (time.time() - cycle_start)
            if sleep > 0:
                time.sleep(sleep)
    except KeyboardInterrupt:
        log(f"Beendet. {total} Positionen erfasst.")
    finally:
        if fh:
            fh.close()

if __name__ == "__main__":
    main()
