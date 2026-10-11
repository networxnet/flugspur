#!/usr/bin/env python3
"""Erzeugt die Beleggrafik zur Abgrenzung des Gebiets Unterbruch.

Zeichnet die massgebliche Gebietsgrenze auf OpenStreetMap-Grundlage, damit
die Festlegung nachvollziehbar ist, ohne fremdes Kartenmaterial zu
uebernehmen.

Aufruf:  python3 doku/bild_unterbruch.py
Ergebnis: doku/belege/unterbruch_grenze_osm.svg

Benoetigt einmalig Netzzugang fuer die Kartenkacheln. Diese werden in die
SVG-Datei eingebettet, das Ergebnis ist danach offline vollstaendig.
"""

import base64
import json
import math
import os
import sys
import time
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(WURZEL, "app"))

URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
UA = "Flugspur/1.0 (Buergerinitiative Fluglaerm; nicht-kommerziell)"
ZOOM = 14
SZ = 820
SPANNE_KM = 5.6


def kachel(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    la = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(la)) / math.pi) / 2.0 * n
    return x, y


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def main():
    zpfad = os.path.join(WURZEL, "app", "plaetze", "zonen_edln.json")
    ort = json.load(open(zpfad, encoding="utf-8"))["orte"]["Schiefbahn-Unterbruch"]
    ring = ort["ringe"][0]
    mla = sum(p[0] for p in ring) / len(ring)
    mlo = sum(p[1] for p in ring) / len(ring)

    m_pro_px = 156543.03 * math.cos(math.radians(mla)) / (2 ** ZOOM)
    px_spanne = SPANNE_KM * 1000.0 / m_pro_px
    mx, my = kachel(mla, mlo, ZOOM)
    x0 = mx - px_spanne / 512.0 / 2
    y0 = my - px_spanne / 512.0 / 2
    x1 = mx + px_spanne / 512.0 / 2
    y1 = my + px_spanne / 512.0 / 2

    def proj(la, lo):
        tx, ty = kachel(la, lo, ZOOM)
        return ((tx - x0) / (x1 - x0) * SZ, (ty - y0) / (y1 - y0) * SZ)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SZ} {SZ}" '
         f'width="{SZ}" height="{SZ}" font-family="system-ui,sans-serif">',
         f'<rect width="{SZ}" height="{SZ}" fill="#eef1ee"/>',
         '<g opacity="0.75">']

    for tx in range(int(math.floor(x0)), int(math.ceil(x1))):
        for ty in range(int(math.floor(y0)), int(math.ceil(y1))):
            u = URL.format(z=ZOOM, x=tx, y=ty)
            try:
                req = urllib.request.Request(u, headers={"User-Agent": UA})
                roh = urllib.request.urlopen(req, timeout=30).read()
            except Exception as e:
                print(f"  Kachel {tx}/{ty} nicht geladen: {e}")
                continue
            time.sleep(0.4)
            px = (tx - x0) / (x1 - x0) * SZ
            py = (ty - y0) / (y1 - y0) * SZ
            br = 1 / (x1 - x0) * SZ
            ho = 1 / (y1 - y0) * SZ
            b64 = base64.b64encode(roh).decode()
            s.append(f'<image x="{px:.2f}" y="{py:.2f}" width="{br:.2f}" '
                     f'height="{ho:.2f}" href="data:image/png;base64,{b64}" '
                     f'preserveAspectRatio="none"/>')
    s.append('</g>')
    s.append(f'<rect width="{SZ}" height="{SZ}" fill="#ffffff" opacity="0.2"/>')

    d = " ".join(("M" if i == 0 else "L") +
                 f"{proj(a, b)[0]:.1f},{proj(a, b)[1]:.1f}"
                 for i, (a, b) in enumerate(ring)) + " Z"
    s.append(f'<path d="{d}" fill="#c2185b" fill-opacity="0.16" '
             f'stroke="#c2185b" stroke-width="3" stroke-linejoin="round"/>')

    # Seitenbeschriftung an die jeweils aeusserste Stelle
    sued = max(ring, key=lambda p: -p[0])
    nord = max(ring, key=lambda p: p[0])
    west = min(ring, key=lambda p: p[1])
    ost = max(ring, key=lambda p: p[1])
    for pkt, txt, dx, dy, anker in (
            (sued, "Süden: A 52", 0, 20, "middle"),
            (nord, "Norden: Römerstraße", 0, -10, "middle"),
            (west, "Westen: L 382", 10, 4, "start"),
            (ost, "Osten: Stadtgrenze Kaarst", -10, 4, "end")):
        x, y = proj(pkt[0], pkt[1])
        x = min(max(x + dx, 10), SZ - 10)
        for stil in ('fill="none" stroke="#ffffff" stroke-width="4"',
                     'fill="#8c0f45"'):
            s.append(f'<text x="{x:.0f}" y="{y+dy:.0f}" font-size="14" '
                     f'font-weight="700" text-anchor="{anker}" {stil}'
                     f'>{esc(txt)}</text>')

    x, y = proj(mla, mlo)
    for stil in ('fill="none" stroke="#ffffff" stroke-width="4"',
                 'fill="#8c0f45"'):
        s.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="17" '
                 f'font-weight="700" text-anchor="middle" {stil}'
                 f'>Unterbruch</text>')
        s.append(f'<text x="{x:.0f}" y="{y+18:.0f}" font-size="12" '
                 f'text-anchor="middle" {stil}>{ort["flaeche_km2"]} km²'
                 f'</text>')

    # Massstab
    lang = 1000.0 / m_pro_px
    s.append(f'<g transform="translate(24,{SZ-28})">'
             f'<line x1="0" y1="0" x2="{lang:.0f}" y2="0" stroke="#111" '
             f'stroke-width="3"/><line x1="0" y1="-5" x2="0" y2="5" '
             f'stroke="#111" stroke-width="3"/><line x1="{lang:.0f}" y1="-5" '
             f'x2="{lang:.0f}" y2="5" stroke="#111" stroke-width="3"/>'
             f'<text x="{lang+8:.0f}" y="5" font-size="13" '
             f'font-weight="600" fill="#111">1 km</text></g>')
    s.append(f'<text x="{SZ-8}" y="{SZ-8}" font-size="11" text-anchor="end" '
             f'fill="#333">© OpenStreetMap-Mitwirkende</text>')
    s.append('</svg>')

    ziel = os.path.join(HIER, "belege", "unterbruch_grenze_osm.svg")
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "w", encoding="utf-8") as f:
        f.write("\n".join(s) + "\n")
    print(f"  {os.path.relpath(ziel, WURZEL)}  "
          f"({os.path.getsize(ziel)//1024} kB, {len(ring)} Grenzpunkte)")


if __name__ == "__main__":
    main()
