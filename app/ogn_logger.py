#!/usr/bin/env python3
"""
EDLN Mitschnitt fuer Luftfahrzeuge OHNE ADS-B:
Open Glider Network (OGN) -- empfaengt FLARM, OGN-Tracker und ADS-L auf 868 MHz.

Das ist die Ergaenzung zu track_logger.py: Segelflugzeuge, Ultraleichte,
Tragschrauber und viele Motorsegler senden FLARM/ADS-L statt ADS-B und sind
deshalb auf adsb.fi/adsb.lol unsichtbar.

Es wird KEINE eigene Hardware benoetigt: wir haengen uns an das offene
APRS-Netz von OGN. Voraussetzung ist lediglich, dass ein OGN-Empfaenger in
Reichweite steht (Abdeckung pruefen: http://ognrange.onglide.com/).
Steht keiner in der Naehe, siehe README -> eigener Empfaenger fuer ~35 EUR.

Start: python3 ogn_logger.py
"""
import socket, time, os, re, json, math, datetime

import profil
import neustart

_P = profil.lade()
SITE = _P["code"]
LAT = _P["lat"]
LON = _P["lon"]
RADIUS_KM = _P["radius_nm"] * 1.852
MAX_ALT = _P["max_alt_ft"]
OUT = profil._env("DATA_DIR") or "/data"
os.makedirs(OUT, exist_ok=True)

APRS_HOST, APRS_PORT = "aprs.glidernet.org", 14580
CALLSIGN = f"FS{_P['code'][:4]}"
FILTER = f"r/{LAT:.4f}/{LON:.4f}/{RADIUS_KM:.0f}"

# OGN-APRS Positionszeile
PAT = re.compile(
    r"^(?P<id>\S+)>.*?:/(?P<time>\d{6})h"
    r"(?P<lat>\d{4}\.\d{2})(?P<ns>[NS]).(?P<lon>\d{5}\.\d{2})(?P<ew>[EW])."
    r"(?P<course>\d{3})/(?P<speed>\d{3})/A=(?P<alt>\d{6})"
)


def log(m):
    print(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [ogn] {m}", flush=True)


def dm2dd(v, hemi):
    d = int(float(v) // 100)
    m = float(v) - d * 100
    dd = d + m / 60.0
    return -dd if hemi in "SW" else dd


def dist_km(la, lo):
    dy = (la - LAT) * 111.32
    dx = (lo - LON) * 111.32 * math.cos(math.radians(LAT))
    return math.hypot(dx, dy)


def run():
    import kennzeichen
    kennzeichen.ddb_aktualisieren(OUT, melde=log)
    namen = kennzeichen.Namen(OUT)
    log(f"Kennzeichen: {namen.umfang[0]} aus ADS-B gelernt, "
        f"{namen.umfang[1]} in der OGN-Geraetedatenbank")
    ddb_zuletzt = time.time()
    _START_STAND = neustart.stand()
    while True:
        neustart.beenden_wenn_neu(_START_STAND, log)
        try:
            log(f"Verbinde {APRS_HOST}:{APRS_PORT} Filter {FILTER}")
            s = socket.create_connection((APRS_HOST, APRS_PORT), timeout=30)
            s.sendall(f"user {CALLSIGN} pass -1 vers flugspur 1.0 filter {FILTER}\n".encode())
            buf = b""
            s.settimeout(60)
            n = 0
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    raise ConnectionError("Verbindung vom Server geschlossen")
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    t = line.decode("utf-8", "replace").strip()
                    if not t or t.startswith("#"):
                        continue
                    m = PAT.match(t)
                    if not m:
                        continue
                    la = dm2dd(m["lat"], m["ns"])
                    lo = dm2dd(m["lon"], m["ew"])
                    d = dist_km(la, lo)
                    if d > RADIUS_KM:
                        continue
                    alt = int(m["alt"])
                    if alt > MAX_ALT:
                        continue          # Reiseflug ist fuer Laerm irrelevant
                    kennung = m["id"]
                    # OGN leitet auch ADS-B weiter. "ICA4D2153" ist dieselbe
                    # Maschine wie "4d2153" im ADS-B-Mitschnitt -- sonst
                    # wuerde sie doppelt gezaehlt.
                    icao = (kennung[3:].lower()
                            if kennung.startswith("ICA") and len(kennung) == 9
                            else None)
                    kz = namen.kennzeichen(hexid=icao, ogn_id=kennung)
                    rec = {
                        "ts": int(time.time()), "id": kennung, "icao": icao,
                        "reg": kz,
                        "typ": namen.muster(hexid=icao, ogn_id=kennung),
                        "lat": round(la, 5),
                        "lon": round(lo, 5), "alt_ft": int(m["alt"]),
                        "course": int(m["course"]), "kt": int(m["speed"]),
                        "d_km": round(d, 2), "raw": t[:200], "net": "OGN", "site": SITE,
                    }
                    day = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
                    with open(os.path.join(OUT, f"ogn_{day}.ndjson"), "a") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
                    with open(os.path.join(OUT, "_heartbeat_ogn.txt"), "w") as hb:
                        hb.write(f"{int(time.time())}\n"
                                 f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"
                                 f"gesamt={n}\n")
                    if n % 100 == 0:
                        log(f"{n} OGN-Positionen erfasst")
                    # einmal taeglich nachsehen, ob neue Geraete gemeldet sind,
                    # und zwischendurch neu von ADS-B Gelerntes uebernehmen
                    if time.time() - ddb_zuletzt > 86400:
                        kennzeichen.ddb_aktualisieren(OUT, melde=log)
                        namen = kennzeichen.Namen(OUT)
                        ddb_zuletzt = time.time()
        except Exception as e:
            log(f"Fehler: {type(e).__name__}: {e} -- neuer Versuch in 30s")
            time.sleep(30)


if __name__ == "__main__":
    log(f"Start {SITE} ({_P['name']}) | {LAT},{LON} | {RADIUS_KM:.0f} km -> {OUT}")
    run()
