#!/usr/bin/env python3
"""Flugplatz-Profile und Einstellungen.

Ein Profil ist eine JSON-Datei unter plaetze/<kuerzel>.json und beschreibt
alles Ortsspezifische: Lage, Pisten, Anrainerorte, Schwellenwerte.

Reihenfolge, in der Werte gesucht werden (spaeter schlaegt frueher):
  1. Vorgaben im Code
  2. Profildatei
  3. Umgebungsvariablen

Damit laesst sich ein Profil im Container punktuell uebersteuern, ohne die
Datei zu aendern.

Auswahl des Profils:
  TRACKER_PLATZ=edln              -> plaetze/edln.json
  TRACKER_PROFIL=/data/mein.json  -> beliebiger Pfad
"""
import json, os, math

BASE = os.path.dirname(os.path.abspath(__file__))
PLATZ_DIR = os.path.join(BASE, "plaetze")

# Altes Praefix bleibt gueltig, damit bestehende Compose-Dateien
# unveraendert weiterlaufen.
PREFIXE = ("TRACKER_", "EDLN_")

VORGABEN = {
    "code": "XXXX",
    "name": "unbenannter Platz",
    "lat": 0.0,
    "lon": 0.0,
    "radius_nm": 15.0,
    "max_alt_ft": 10000.0,
    "interval_s": 5.0,
    "low_ft": 2500.0,
    "overflight_km": 1.0,
    "view_km": 11.0,
    "platzrunde": True,      # Platzrundenerkennung sinnvoll? (Kleinflugplatz)
    "runways": [],           # [{"id": "13", "heading": 135}, ...]
    "orte": [],              # [{"name": "...", "lat": .., "lon": ..}, ...]
    "hinweis": "",
}

def _env(name):
    for p in PREFIXE:
        v = os.environ.get(p + name.upper())
        if v not in (None, ""):
            return v
    return None

def _cast(v, muster):
    if isinstance(muster, bool):
        return str(v).strip().lower() not in ("", "0", "false", "nein", "no")
    if isinstance(muster, float):
        return float(v)
    if isinstance(muster, int):
        return int(v)
    return v

def verfuegbare_plaetze():
    if not os.path.isdir(PLATZ_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(PLATZ_DIR) if f.endswith(".json"))

def lade():
    """Liefert das wirksame Profil als dict."""
    p = dict(VORGABEN)

    pfad = _env("PROFIL")
    code = _env("PLATZ")
    if not pfad and code:
        pfad = os.path.join(PLATZ_DIR, f"{code.strip().lower()}.json")

    if pfad:
        if not os.path.exists(pfad):
            raise SystemExit(
                f"Profil nicht gefunden: {pfad}\n"
                f"Verfuegbar: {', '.join(verfuegbare_plaetze()) or '(keine)'}\n"
                f"Setzen Sie TRACKER_PLATZ (Kuerzel) oder TRACKER_PROFIL (Pfad)."
            )
        with open(pfad, encoding="utf-8") as f:
            p.update(json.load(f))

    # Umgebungsvariablen haben das letzte Wort
    for k, muster in VORGABEN.items():
        if k in ("runways", "orte"):
            continue
        v = _env(k)
        if v is not None:
            p[k] = _cast(v, muster)
    # SITE als Alias fuer code (Rueckwaertskompatibilitaet)
    site = _env("SITE")
    if site:
        p["code"] = site

    p["orte"] = [(o["name"], float(o["lat"]), float(o["lon"]))
                 for o in p.get("orte", [])]
    return p

def km_pro_grad(lat):
    return 111.32, 111.32 * math.cos(math.radians(lat))

def hav_km(la1, lo1, la2, lo2):
    r = 6371.0
    f1, f2 = math.radians(la1), math.radians(la2)
    dp = math.radians(la2 - la1)
    dl = math.radians(lo2 - lo1)
    a = math.sin(dp/2)**2 + math.cos(f1)*math.cos(f2)*math.sin(dl/2)**2
    return 2 * r * math.asin(math.sqrt(a))

def winkel_diff(a, b):
    return abs((a - b + 180) % 360 - 180)

if __name__ == "__main__":
    import sys
    pr = lade()
    print(f"Verfuegbare Profile: {', '.join(verfuegbare_plaetze()) or '(keine)'}")
    print(f"\nWirksames Profil: {pr['code']} -- {pr['name']}")
    print(f"  Lage         {pr['lat']}, {pr['lon']}")
    print(f"  Radius       {pr['radius_nm']} NM")
    print(f"  Hoehenfilter < {pr['max_alt_ft']:.0f} ft")
    print(f"  Takt         {pr['interval_s']} s")
    print(f"  Platzrunde   {'ja' if pr['platzrunde'] else 'nein'}")
    print(f"  Pisten       {', '.join(f'{r[chr(105)+chr(100)]} ({r[chr(104)+chr(101)+chr(97)+chr(100)+chr(105)+chr(110)+chr(103)]} Grad)' for r in pr['runways']) or '(keine)'}")
    print(f"  Ortslagen    {len(pr['orte'])}")
    for n, la, lo in pr["orte"]:
        print(f"      {n:34s} {la:.4f},{lo:.4f}  {hav_km(pr['lat'],pr['lon'],la,lo):5.1f} km")
    if pr.get("hinweis"):
        print(f"\n  Hinweis: {pr['hinweis']}")
