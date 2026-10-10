#!/usr/bin/env python3
"""Erzeugt aus dem Mitschnitt eine eigenstaendige HTML-Seite fuer Laien.

Alles ist in die Datei eingebettet (SVG, Stile) -- kein Internet, keine
Kartendienste, keine Schriftarten von aussen. Die Datei laesst sich per
Mail verschicken, auf einem Beamer oeffnen und ausdrucken.

Aufruf:
  python3 visualize.py                 letzter Tag
  python3 visualize.py 2026-10-07      bestimmter Tag
  python3 visualize.py --all           alle Tage zusammengefasst
"""
import json, os, sys, math, glob, html
from collections import defaultdict
from datetime import datetime

import profil, kennzeichen

_P       = profil.lade()
LAT      = _P["lat"]
LON      = _P["lon"]
DATA_DIR = profil._env("DATA_DIR") or "/data"
OUT_DIR  = profil._env("OUT_DIR") or DATA_DIR
OVER_KM  = _P["overflight_km"]
ZONEN    = profil.lade_zonen(_P)
FELDER   = profil.lade_zonenfelder(_P, ZONEN)
LAERM_M  = float(_P.get("laerm_schraeg_m") or 1500)
FARBEN   = ["#c2185b", "#1565c0", "#2e7d32", "#ef6c00", "#6a1b9a",
            "#00838f", "#9e5b00", "#4e342e", "#546e7a", "#ad1457"]
def _grundkarte():
    pf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "plaetze", f"grundkarte_{_P['code'].lower()}.json")
    if not os.path.exists(pf):
        return None
    try:
        with open(pf, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
GRUND = _grundkarte()
LOW_FT   = _P["low_ft"]
VIEW_KM  = _P["view_km"]
RUNWAYS  = _P["runways"]
ORTE     = _P["orte"]
DEMO     = (profil._env("DEMO") or "") not in ("", "0", "false")
DEBOUNCE = 180


# Hoehenbaender: je tiefer, desto lauter am Boden
BANDS = [
    (0,    1000, "#d7191c", "unter 1000 ft (ca. 300 m) — sehr laut"),
    (1000, 1500, "#fdae61", "1000–1500 ft (300–460 m) — deutlich hoerbar"),
    (1500, 2500, "#ffd92f", "1500–2500 ft (460–760 m) — hoerbar"),
    (2500, 99999, "#4575b4", "ueber 2500 ft — meist Durchgangsverkehr"),
]

KM_LAT, KM_LON = profil.km_pro_grad(LAT)
hav_km = profil.hav_km

def band_color(alt):
    if alt is None:
        return "#999999"
    for lo, hi, col, _ in BANDS:
        if lo <= alt < hi:
            return col
    return "#4575b4"

# ---------------------------------------------------------------- Daten laden


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

def load(days):
    pts = []
    for day in days:
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
                    N = _namen()
                    if r.get("net") == "OGN":
                        p = {"t": r.get("ts"), "id": _ogn_id(r), "lat": r.get("lat"),
                             "lon": r.get("lon"), "alt": r.get("alt_ft"),
                             "desc": N.muster(hexid=r.get("icao"),
                                              ogn_id=r.get("id"),
                                              desc=r.get("typ")),
                             "kz": N.anzeige(hexid=r.get("icao"),
                                             ogn_id=r.get("id"),
                                             reg=r.get("reg")),
                             "net": "OGN"}
                    else:
                        N.lerne(r.get("icao"), r.get("reg"),
                                r.get("type"), r.get("desc"))
                        p = {"t": r.get("t"), "id": r.get("icao"), "lat": r.get("lat"),
                             "lon": r.get("lon"), "alt": r.get("alt_ft"),
                             "desc": r.get("desc") or r.get("type"),
                             "kz": N.anzeige(hexid=r.get("icao"), reg=r.get("reg")),
                             "net": "ADSB"}
                    if (p["t"] and p["id"] and p["lat"] is not None
                            and (p["alt"] is None or p["alt"] <= _P["max_alt_ft"])):
                        pts.append(p)
    pts.sort(key=lambda p: p["t"])
    return pts

# ------------------------------------------------------------------ Geometrie

SZ = 900          # Kantenlaenge der Karte in px


def grundkarte_svg():
    """Eingebettete OSM-Kacheln als Kartenhintergrund."""
    if not GRUND:
        return []
    out = ['<g opacity="0.62">']
    for k in GRUND["kacheln"]:
        x1, y1 = proj(k["n"], k["w"])
        x2, y2 = proj(k["s"], k["e"])
        out.append(f'<image x="{x1:.2f}" y="{y1:.2f}" '
                   f'width="{x2-x1:.2f}" height="{y2-y1:.2f}" '
                   f'preserveAspectRatio="none" '
                   f'href="data:image/png;base64,{k["b64"]}"/>')
    out.append('</g>')
    out.append(f'<rect x="0" y="0" width="{SZ}" height="{SZ}" '
               f'fill="#ffffff" opacity="0.18"/>')
    return out


def zonen_svg(mit_namen=True):
    """Ortslagen als je eine zusammenhaengende, farbige Flaeche.

    Die bebauten OSM-Teilflaechen werden ueber ein Raster mit 200 m
    Toleranz verschmolzen und als geschlossener Umriss gezeichnet --
    sonst zerfaellt ein Ort optisch in Dutzende Schnipsel.
    """
    out = []
    for idx, (name, la, lo) in enumerate(ORTE):
        feld = FELDER.get(name)
        if not feld:
            continue
        ringe = feld.umriss(200)
        if not ringe:
            continue
        d = []
        for r in ringe:
            d.append(" ".join(("M" if i == 0 else "L") +
                              f"{proj(a, b)[0]:.1f},{proj(a, b)[1]:.1f}"
                              for i, (a, b) in enumerate(r)) + " Z")
        farbe = FARBEN[idx % len(FARBEN)]
        out.append(f'<path d="{" ".join(d)}" fill="{farbe}" fill-opacity="0.26" '
                   f'fill-rule="evenodd" stroke="{farbe}" stroke-width="2.4" '
                   f'stroke-linejoin="round" stroke-opacity="0.95"/>')
    if mit_namen:
        for idx, (name, la, lo) in enumerate(ORTE):
            if name not in FELDER:
                continue
            x, y = proj(la, lo)
            if not (0 <= x <= SZ and 0 <= y <= SZ):
                continue
            kurz = name.split("-", 1)[1] if "-" in name else name
            for lage in ("unten", "oben"):
                if lage == "unten":
                    stil = ('fill="none" stroke="#ffffff" stroke-width="3.6" '
                            'stroke-linejoin="round"')
                else:
                    stil = f'fill="{FARBEN[idx % len(FARBEN)]}"'
                out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="13" '
                           f'font-weight="700" text-anchor="middle" {stil}'
                           f'>{esc(kurz)}</text>')
    return out


def nordpfeil_svg():
    """Nordpfeil und Massstab -- damit die Ausrichtung sichtbar belegt ist."""
    out = []
    # Nordpfeil oben rechts
    bx, by = SZ - 52, 20
    out.append(f'<g><rect x="{bx-20}" y="{by-6}" width="46" height="74" rx="7" '
               f'fill="#ffffff" fill-opacity="0.85" stroke="#c9d3dd"/>'
               f'<polygon points="{bx+3},{by+2} {bx+12},{by+40} {bx+3},{by+33} '
               f'{bx-6},{by+40}" fill="#1b2430"/>'
               f'<text x="{bx+3}" y="{by+60}" font-size="14" font-weight="700" '
               f'text-anchor="middle" fill="#1b2430">N</text></g>')
    # Massstabsbalken unten links
    for km in (5, 2, 1):
        laenge = km / VIEW_KM * (SZ / 2)
        if laenge <= SZ * 0.33:
            break
    x0, y0 = 24, SZ - 28
    out.append(f'<g><rect x="{x0-7}" y="{y0-21}" width="{laenge+56}" height="32" '
               f'rx="6" fill="#ffffff" fill-opacity="0.85" stroke="#c9d3dd"/>'
               f'<line x1="{x0}" y1="{y0}" x2="{x0+laenge}" y2="{y0}" '
               f'stroke="#1b2430" stroke-width="3"/>'
               f'<line x1="{x0}" y1="{y0-5}" x2="{x0}" y2="{y0+5}" '
               f'stroke="#1b2430" stroke-width="3"/>'
               f'<line x1="{x0+laenge}" y1="{y0-5}" x2="{x0+laenge}" y2="{y0+5}" '
               f'stroke="#1b2430" stroke-width="3"/>'
               f'<text x="{x0+laenge+10}" y="{y0+4}" font-size="12" '
               f'font-weight="600" fill="#1b2430">{km} km</text></g>')
    if GRUND:
        out.append(f'<text x="{SZ-6}" y="{SZ-6}" font-size="10" '
                   f'text-anchor="end" fill="#44505e" stroke="#ffffff" '
                   f'stroke-width="2.6" paint-order="stroke">'
                   f'Kartengrundlage \u00a9 OpenStreetMap-Mitwirkende (ODbL)</text>')
    return out


def proj(lat, lon):
    x = SZ/2 + (lon - LON) * KM_LON / VIEW_KM * (SZ/2)
    y = SZ/2 - (lat - LAT) * KM_LAT / VIEW_KM * (SZ/2)
    return x, y

def esc(s):
    return html.escape(str(s), quote=True)

# ---------------------------------------------------------------------- Karte

def karte(pts):
    s = [f'<svg viewBox="0 0 {SZ} {SZ}" xmlns="http://www.w3.org/2000/svg" '
         f'style="width:100%;height:auto;background:#f7f9fb;border:1px solid #ccd">']
    s += grundkarte_svg()
    s += zonen_svg()

    # Entfernungsringe
    for km in (2, 4, 6, 8, 10):
        r = km / VIEW_KM * (SZ/2)
        s.append(f'<circle cx="{SZ/2}" cy="{SZ/2}" r="{r:.1f}" fill="none" '
                 f'stroke="#dde3ea" stroke-width="1"/>')
        s.append(f'<text x="{SZ/2+r-4:.1f}" y="{SZ/2-4}" font-size="11" '
                 f'fill="#9aa6b2" text-anchor="end">{km} km</text>')

    # Landebahnen aus dem Profil
    hl = 0.6
    for rw in RUNWAYS[:2] or [{"heading": 0}]:
        a = math.radians(rw["heading"])
        dx, dy = math.sin(a) * hl, math.cos(a) * hl
        x1, y1 = proj(LAT - dy/KM_LAT, LON - dx/KM_LON)
        x2, y2 = proj(LAT + dy/KM_LAT, LON + dx/KM_LON)
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="#222" stroke-width="5" stroke-linecap="round"/>')
    s.append(f'<text x="{SZ/2+10}" y="{SZ/2+22}" font-size="13" font-weight="600" '
             f'fill="#222">{esc(_P["name"])} ({esc(_P["code"])})</text>')

    # Flugspuren
    by_ac = defaultdict(list)
    for p in pts:
        by_ac[p["id"]].append(p)
    for acid, tr in by_ac.items():
        seg = []
        prev_t = None
        for p in tr:
            if prev_t is not None and p["t"] - prev_t > 120:
                _draw_seg(s, seg)
                seg = []
            seg.append(p)
            prev_t = p["t"]
        _draw_seg(s, seg)

    # Ortslagen: Zonen sind schon gezeichnet, hier nur die ohne Umriss
    for name, ola, olo in ORTE:
        if name in ZONEN:
            continue
        x, y = proj(ola, olo)
        if not (0 <= x <= SZ and 0 <= y <= SZ):
            continue
        rr = OVER_KM / VIEW_KM * (SZ/2)
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="#1a1a1a" '
                 f'fill-opacity="0.05" stroke="#555" stroke-width="1" '
                 f'stroke-dasharray="4 3"/>')
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#111"/>')
        s.append(f'<text x="{x:.1f}" y="{y-10:.1f}" font-size="13" font-weight="600" '
                 f'fill="#111" text-anchor="middle" '
                 f'style="paint-order:stroke;stroke:#fff;stroke-width:3px">'
                 f'{esc(name)}</text>')

    s += nordpfeil_svg()
    s.append('</svg>')
    return "\n".join(s)

def _draw_seg(s, seg):
    if len(seg) < 2:
        return
    # in Teilstuecke gleicher Hoehenklasse zerlegen
    cur, curcol = [], None
    for p in seg:
        col = band_color(p["alt"])
        if curcol is None:
            curcol = col
        if col != curcol and len(cur) >= 2:
            _poly(s, cur, curcol)
            cur = [cur[-1]]
            curcol = col
        cur.append(p)
    if len(cur) >= 2:
        _poly(s, cur, curcol)

def _poly(s, seg, col):
    d = " ".join(f"{proj(p['lat'], p['lon'])[0]:.1f},{proj(p['lat'], p['lon'])[1]:.1f}"
                 for p in seg)
    s.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="2" '
             f'stroke-opacity="0.75" stroke-linejoin="round" stroke-linecap="round"/>')

# -------------------------------------------------------------------- Heatmap

def heatmap(pts):
    cell_km = 0.5
    n = int(VIEW_KM * 2 / cell_km)
    grid = defaultdict(set)
    for p in pts:
        if p["alt"] is None or p["alt"] > LOW_FT:
            continue
        gx = int((p["lon"] - LON) * KM_LON / cell_km) + n//2
        gy = int(-(p["lat"] - LAT) * KM_LAT / cell_km) + n//2
        if 0 <= gx < n and 0 <= gy < n:
            grid[(gx, gy)].add((p["id"], int(p["t"]) // DEBOUNCE))
    if not grid:
        return None, 0
    counts = {k: len(v) for k, v in grid.items()}
    mx = max(counts.values())
    cs = SZ / n
    s = [f'<svg viewBox="0 0 {SZ} {SZ}" xmlns="http://www.w3.org/2000/svg" '
         f'style="width:100%;height:auto;background:#fcfcfd;border:1px solid #ccd">']
    for (gx, gy), c in sorted(counts.items(), key=lambda kv: kv[1]):
        f = (c / mx) ** 0.55
        r = int(255 - 180*f); g = int(240 - 215*f); b = int(245 - 185*f)
        s.append(f'<rect x="{gx*cs:.1f}" y="{gy*cs:.1f}" width="{cs:.1f}" '
                 f'height="{cs:.1f}" fill="rgb({r},{g},{b})" fill-opacity="0.92"/>')
    for idx, (name, _, _) in enumerate(ORTE):
        feld = FELDER.get(name)
        if not feld:
            continue
        d = []
        for r in feld.umriss(200):
            d.append(" ".join(("M" if i == 0 else "L") +
                              f"{proj(a, b)[0]:.1f},{proj(a, b)[1]:.1f}"
                              for i, (a, b) in enumerate(r)) + " Z")
        if d:
            s.append(f'<path d="{" ".join(d)}" fill="none" '
                     f'stroke="{FARBEN[idx % len(FARBEN)]}" stroke-width="2.2" '
                     f'stroke-linejoin="round" stroke-opacity="0.9"/>')
    for name, ola, olo in ORTE:
        x, y = proj(ola, olo)
        if 0 <= x <= SZ and 0 <= y <= SZ:
            if name not in ZONEN:
                s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#000"/>')
            s.append(f'<text x="{x:.1f}" y="{y-9:.1f}" font-size="12" font-weight="600" '
                     f'fill="#000" text-anchor="middle" '
                     f'style="paint-order:stroke;stroke:#fff;stroke-width:3px">'
                     f'{esc(name)}</text>')
    x1, y1 = proj(LAT, LON)
    s.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="5" fill="none" stroke="#000" stroke-width="2"/>')
    s += nordpfeil_svg()
    s.append('</svg>')
    return "\n".join(s), mx

# --------------------------------------------------------------- Balkengrafik

def bars(rows, unit="", color="#2c7fb8", maxw=560):
    if not rows:
        return "<p><em>keine Daten</em></p>"
    mx = max(v for _, v, _ in rows) or 1
    out = ['<table style="border-collapse:collapse;width:100%">']
    for label, val, note in rows:
        w = val / mx * maxw
        out.append(
            f'<tr>'
            f'<td style="padding:4px 10px 4px 0;font-size:14px;white-space:nowrap">{esc(label)}</td>'
            f'<td style="width:100%;padding:4px 0">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<div style="height:18px;width:{w:.0f}px;min-width:2px;background:{color};'
            f'border-radius:3px"></div>'
            f'<span style="font-size:14px;font-weight:600">{val}{esc(unit)}</span>'
            f'<span style="font-size:12px;color:#667">{esc(note)}</span>'
            f'</div></td></tr>')
    out.append('</table>')
    return "\n".join(out)

# ------------------------------------------------------------------ Auswertung

def ueberfluege(pts):
    res = {}
    for name, ola, olo in ORTE:
        last, ev = {}, []
        feld = FELDER.get(name)
        for p in pts:
            if (feld.schraeg_m(p["lat"], p["lon"], p["alt"]) <= LAERM_M if feld
                    else hav_km(ola, olo, p["lat"], p["lon"]) <= OVER_KM):
                prev = last.get(p["id"])
                if prev is None or p["t"] - prev > DEBOUNCE:
                    ev.append(p)
                last[p["id"]] = p["t"]
        res[name] = ev
    return res

def build(days, outfile):
    pts = load(days)
    if not pts:
        print(f"Keine Daten fuer {', '.join(days)}")
        return False

    by_ac = defaultdict(list)
    for p in pts:
        by_ac[p["id"]].append(p)
    t0, t1 = pts[0]["t"], pts[-1]["t"]
    span_h = (t1 - t0) / 3600.0
    ev = ueberfluege(pts)
    hm, hm_max = heatmap(pts)

    zeitraum = (f"{datetime.fromtimestamp(t0):%d.%m.%Y %H:%M} bis "
                f"{datetime.fromtimestamp(t1):%d.%m.%Y %H:%M} Uhr")

    # Ortsbalken
    orte_rows = []
    for name, _, _ in ORTE:
        e = ev[name]
        alts = [x["alt"] for x in e if x["alt"] is not None]
        note = ""
        if alts:
            tief = sum(1 for a in alts if a < 1500)
            note = f"niedrigster {min(alts):.0f} ft, davon {tief} unter 1500 ft"
        orte_rows.append((name, len(e), note))
    orte_rows.sort(key=lambda r: -r[1])

    # Stundenverteilung
    std = defaultdict(set)
    for p in pts:
        if p["alt"] is not None and p["alt"] <= LOW_FT:
            std[datetime.fromtimestamp(p["t"]).hour].add(p["id"])
    std_rows = [(f"{h:02d}:00", len(std.get(h, set())), "")
                for h in range(min(std) if std else 0, (max(std)+1) if std else 1)]

    # Muster
    typen = defaultdict(set)
    for acid, tr in by_ac.items():
        d = next((x["desc"] for x in tr if x["desc"]), None)
        typen[d or "ohne Typkennung (meist Segelflug/UL)"].add(acid)
    typ_rows = sorted(((k, len(v), "") for k, v in typen.items()),
                      key=lambda r: -r[1])[:15]

    legende = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:18px;'
        f'font-size:13px"><span style="width:22px;height:5px;background:{c};'
        f'border-radius:2px;display:inline-block"></span>{esc(t)}</span>'
        for _, _, c, t in BANDS)

    gesamt_ev = sum(len(v) for v in ev.values())
    tief_ev = sum(1 for v in ev.values() for x in v
                  if x["alt"] is not None and x["alt"] < 1500)

    H = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flugbewegungen {esc(_P["name"])} — {esc(days[0])}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  max-width:1000px;margin:0 auto;padding:28px 20px 60px;color:#1b2430;line-height:1.55}}
 h1{{font-size:27px;margin:0 0 4px}} h2{{font-size:20px;margin:38px 0 10px;
  border-bottom:2px solid #e4e9ef;padding-bottom:6px}}
 .sub{{color:#667;font-size:15px;margin-bottom:22px}}
 .kpis{{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0 6px}}
 .kpi{{flex:1 1 150px;background:#f3f6f9;border:1px solid #e1e8ef;border-radius:8px;
  padding:12px 14px}}
 .kpi b{{display:block;font-size:26px;line-height:1.15}}
 .kpi span{{font-size:12px;color:#5a6673}}
 .note{{background:#fff8e6;border-left:4px solid #e8b931;padding:11px 15px;
  margin:16px 0;font-size:14px;border-radius:0 5px 5px 0}}
 .lead{{background:#eef4fa;border-left:4px solid #2c7fb8;padding:11px 15px;
  margin:14px 0;font-size:14px;border-radius:0 5px 5px 0}}
 footer{{margin-top:44px;font-size:12px;color:#78828d;border-top:1px solid #e4e9ef;
  padding-top:14px}}
</style></head><body>

{'<div style="background:#b3261e;color:#fff;padding:13px 17px;border-radius:7px;margin-bottom:20px;font-size:15px"><b>BEISPIEL MIT SIMULIERTEN DATEN.</b> Diese Seite zeigt nur, wie die Auswertung aussieht. Die Flugspuren sind erfunden und belegen nichts. Echte Auswertungen tragen diesen Hinweis nicht.</div>' if DEMO else ''}
<h1>Flugbewegungen {esc(_P["name"])} ({esc(_P["code"])})</h1>
<div class="sub">Eigener Mitschnitt &middot; {esc(zeitraum)} &middot; Erfassungsdauer {span_h:.1f} Stunden</div>

<div class="kpis">
 <div class="kpi"><b>{len(by_ac)}</b><span>verschiedene Luftfahrzeuge</span></div>
 <div class="kpi"><b>{len(pts)}</b><span>aufgezeichnete Positionen</span></div>
 <div class="kpi"><b>{gesamt_ev}</b><span>Ortsüberflüge</span></div>
 <div class="kpi"><b>{tief_ev}</b><span>davon unter 1500 ft</span></div>
</div>

<div class="lead"><b>Wie diese Auswertung entstanden ist:</b> Jede Linie und jede
Zahl stammt aus Signalen, die die Flugzeuge selbst aussenden und die öffentlich
empfangbar sind. Es wurde nichts geschätzt, modelliert oder hochgerechnet.</div>

<h2>1. Wo wurde geflogen?</h2>
<p>Jede Linie ist der tatsächliche Weg eines Flugzeugs. Die Farbe zeigt die Höhe
über Grund — <b>je röter, desto tiefer und damit lauter am Boden</b>. Die
farbigen Flächen sind die tatsächlich bebauten Ortslagen laut
OpenStreetMap. Norden ist oben, der Maßstab steht unten links.</p>
<p>{legende}</p>
{karte(pts)}

<h2>2. Wo verdichtet sich die Belastung?</h2>
<p>Dieselben Daten als Dichtekarte: Nur Flüge unterhalb {LOW_FT:.0f} ft werden
gezählt, also der tief fliegende Verkehr. <b>Je dunkler ein Feld, desto öfter
wurde es überflogen.</b> So wird sichtbar, ob sich der Verkehr an die
empfohlene Platzrunde hält oder eigene Wege nimmt.</p>
{hm if hm else '<p><em>Zu wenig Tiefflugdaten für eine Dichtekarte.</em></p>'}
<p style="font-size:13px;color:#667">Dunkelstes Feld: {hm_max} Durchgänge auf
500 × 500 Metern.</p>

<h2>3. Welcher Ort ist wie stark betroffen?</h2>
<p>Gezählt wird jeder Durchgang, bei dem die <b>Schrägentfernung</b> zur
bebauten Fläche {LAERM_M:.0f} m oder weniger betrug — also auch ein Flug
dicht daneben, nicht nur der direkte Überflug.
Eine kreisende Maschine zählt pro Runde einmal — nicht pro Sekunde.</p>
{bars(orte_rows, color="#c0392b")}

<h2>4. Wann wurde geflogen?</h2>
<p>Verschiedene tief fliegende Luftfahrzeuge je Tagesstunde.</p>
{bars(std_rows, color="#2c7fb8")}

<h2>5. Was ist geflogen?</h2>
<p>Anzahl verschiedener Maschinen je Typ. Kleine Kolbenflugzeuge wie Piper
PA-28 oder Cessna 172 stehen typischerweise für Schul- und Platzrundenbetrieb.</p>
{bars(typ_rows, color="#4a7c59")}

<div class="note"><b>Was diese Zahlen nicht sagen.</b> Erfasst werden nur
Maschinen mit ADS-B, MLAT-fähigem Mode-S oder FLARM. Am Flughafen
{esc(_P["name"])} besteht unter Umständen <b>keine Transponderpflicht</b> — Maschinen mit
reinem Mode-A/C-Gerät bleiben unsichtbar. Alle Stückzahlen sind deshalb
<b>Untergrenzen</b>: Es war mindestens so viel Verkehr, nie weniger.<br><br>
Ein Überflug über Schiefbahn/Unterbruch ist zudem <b>kein Rechtsverstoß</b>.
Die Vereinbarung, diesen Bereich zu meiden, ist nicht rechtsverbindlich, und
eine verbindliche Mindestflughöhe gibt es dort nicht. Diese Auswertung belegt
das <b>tatsächliche Ausmaß</b> der Belastung — nicht ein Fehlverhalten.</div>

<footer>
Datenquellen: offene ADS-B-Netze (adsb.fi, adsb.lol) und Open Glider Network.
Erfassung durch eigenen Mitschnitt, Bezugspunkt {LAT:.4f} / {LON:.4f}.
Erstellt am {datetime.now():%d.%m.%Y um %H:%M} Uhr.
</footer>
</body></html>"""

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(H)
    print(f"Geschrieben: {outfile}  ({os.path.getsize(outfile)/1024:.0f} kB)")
    print(f"  {len(by_ac)} Luftfahrzeuge, {len(pts)} Positionen, {gesamt_ev} Ortsueberfluege")
    return True

def available_days():
    d = set()
    for p in glob.glob(os.path.join(DATA_DIR, "*_????-??-??.ndjson")):
        d.add(os.path.basename(p).rsplit("_", 1)[1][:10])
    return sorted(d)

def main():
    days = available_days()
    if not days:
        print(f"Keine Mitschnittdateien in {DATA_DIR}")
        sys.exit(1)
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "--all":
        build(days, os.path.join(OUT_DIR, "flugbewegungen_gesamt.html"))
    else:
        day = arg or days[-1]
        build([day], os.path.join(OUT_DIR, f"flugbewegungen_{day}.html"))

if __name__ == "__main__":
    main()
