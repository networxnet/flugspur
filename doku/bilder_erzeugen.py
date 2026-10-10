#!/usr/bin/env python3
"""Erzeugt die Abbildungen fuer doku/METHODIK.md als SVG.

SVG, weil GitHub es direkt anzeigt, es in der Versionsverwaltung als Text
lesbar bleibt und keine Laufzeitumgebung zum Betrachten noetig ist.

Aufruf:  python3 doku/bilder_erzeugen.py
"""

import math
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HIER), "app"))

import laerm  # noqa: E402

ZIEL = os.path.join(HIER, "bilder")
os.makedirs(ZIEL, exist_ok=True)

FARBE = {"P1.0": "#2e7d32", "P1.2": "#1565c0", "P1.4": "#ef6c00",
         "P2.1": "#6a1b9a", "H": "#00838f", "S": "#c2185b"}


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


# ---------------------------------------------------------------- Abbildung 1
def pegel_entfernung():
    """Pegelverlauf ueber der Schraegentfernung, je Luftfahrzeuggruppe."""
    B, H = 760, 460
    L, R, O, U = 70, 215, 30, 55          # Raender
    x0, x1 = 0.0, 4000.0                   # Meter
    y0, y1 = 40.0, 95.0                    # dB(A)

    def px(m):
        return L + (m - x0) / (x1 - x0) * (B - L - R)

    def py(db):
        return O + (y1 - db) / (y1 - y0) * (H - O - U)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B} {H}" '
         f'width="{B}" height="{H}" font-family="system-ui,sans-serif">',
         f'<rect width="{B}" height="{H}" fill="#ffffff"/>']

    # Schwellenbaender
    s.append(f'<rect x="{L}" y="{py(y1):.1f}" width="{B-L-R}" '
             f'height="{py(65)-py(y1):.1f}" fill="#c2185b" opacity="0.07"/>')
    s.append(f'<rect x="{L}" y="{py(65):.1f}" width="{B-L-R}" '
             f'height="{py(55)-py(65):.1f}" fill="#ef6c00" opacity="0.07"/>')

    # Gitter und Achsen
    for m in range(0, 4001, 250):
        voll = m % 1000 == 0
        s.append(f'<line x1="{px(m):.1f}" y1="{O}" x2="{px(m):.1f}" '
                 f'y2="{H-U}" stroke="{"#d7dde4" if voll else "#eef2f6"}"/>')
        if voll:
            s.append(f'<text x="{px(m):.1f}" y="{H-U+18}" font-size="12" '
                     f'text-anchor="middle" fill="#55606e">'
                     f'{m // 1000}</text>')
    for db in range(40, 96, 5):
        stark = db in (55, 65)
        s.append(f'<line x1="{L}" y1="{py(db):.1f}" x2="{B-R}" '
                 f'y2="{py(db):.1f}" stroke="{"#99a4b2" if stark else "#e3e8ee"}" '
                 f'{"stroke-dasharray=\'5 4\'" if stark else ""}/>')
        s.append(f'<text x="{L-9}" y="{py(db)+4:.1f}" font-size="12" '
                 f'text-anchor="end" fill="#55606e">{db}</text>')

    s.append(f'<text x="{(L+B-R)/2:.0f}" y="{H-12}" font-size="13" '
             f'text-anchor="middle" fill="#2b3440">'
             f'Schrägentfernung zum Ohr in km</text>')
    s.append(f'<text transform="translate(18,{(O+H-U)/2:.0f}) rotate(-90)" '
             f'font-size="13" text-anchor="middle" fill="#2b3440">'
             f'geschätzter Maximalpegel in dB(A)</text>')

    # Kurven
    for g in ("S", "P2.1", "H", "P1.4", "P1.2", "P1.0"):
        pts = []
        for i in range(0, 481):
            m = x0 + (x1 - x0) * i / 480
            db = laerm.pegel_db(g, max(m, 60))
            if db > y1 or db < y0:     # nicht am Rand kleben lassen
                continue
            pts.append(f"{px(m):.1f},{py(db):.1f}")
        if not pts:
            continue
        # Hubschrauber und schwere Propeller haben denselben Bezugspegel;
        # gestrichelt, damit beide Kurven unterscheidbar bleiben.
        strich = ' stroke-dasharray="7 5"' if g == "H" else ""
        s.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                 f'stroke="{FARBE[g]}" stroke-width="2.6" '
                 f'stroke-linejoin="round"{strich}/>')

    # Beschriftung rechts, nach Pegel bei 4000 m sortiert
    eintraege = sorted((("S", "Strahlflugzeug"), ("P2.1", "Propeller > 5,7 t"),
                        ("H", "Hubschrauber"), ("P1.4", "Propeller 2–5,7 t"),
                        ("P1.2", "Propeller bis 2 t"), ("P1.0", "Ultraleicht")),
                       key=lambda e: -laerm.pegel_db(e[0], 4000))
    y = O + 14
    for g, text in eintraege:
        s.append(f'<line x1="{B-R+6}" y1="{y-4:.0f}" x2="{B-R+26}" '
                 f'y2="{y-4:.0f}" stroke="{FARBE[g]}" stroke-width="3"/>')
        s.append(f'<text x="{B-R+32}" y="{y:.0f}" font-size="12.5" '
                 f'fill="#2b3440">{esc(text)}</text>')
        s.append(f'<text x="{B-R+32}" y="{y+14:.0f}" font-size="11" '
                 f'fill="#7a8694">{laerm.BEZUGSPEGEL_300M[g]:.1f} dB(A) '
                 f'in 300 m</text>'.replace(".", ","))
        y += 38

    # Schwellenbeschriftung
    s.append(f'<text x="{L+8}" y="{py(65)-7:.1f}" font-size="11.5" '
             f'fill="#c2185b">65 dB(A) – Tag-Schutzzone 1 FluLärmG</text>')
    s.append(f'<text x="{L+8}" y="{py(55)-7:.1f}" font-size="11.5" '
             f'fill="#b35b00">55 dB(A) – Orientierungswert DIN 18005, '
             f'Wohngebiet tags</text>')
    s.append('</svg>')
    schreiben("pegel_entfernung.svg", "\n".join(s))


# ---------------------------------------------------------------- Abbildung 2
def erfassungskette():
    """Was woher kommt und was daraus wird."""
    B, H = 820, 430
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B} {H}" '
         f'width="{B}" height="{H}" font-family="system-ui,sans-serif">',
         f'<rect width="{B}" height="{H}" fill="#ffffff"/>']

    def kasten(x, y, w, h, titel, zeilen, farbe):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" '
                 f'fill="{farbe}" fill-opacity="0.09" stroke="{farbe}" '
                 f'stroke-width="1.6"/>')
        s.append(f'<text x="{x+12}" y="{y+21}" font-size="13.5" '
                 f'font-weight="700" fill="{farbe}">{esc(titel)}</text>')
        for i, z in enumerate(zeilen):
            s.append(f'<text x="{x+12}" y="{y+41+i*16}" font-size="11.5" '
                     f'fill="#43505e">{esc(z)}</text>')

    def pfeil(x1, y1, x2, y2):
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                 f'stroke="#8c98a6" stroke-width="1.8" '
                 f'marker-end="url(#sp)"/>')

    s.append('<defs><marker id="sp" markerWidth="9" markerHeight="9" '
             'refX="8" refY="3" orient="auto">'
             '<path d="M0,0 L8,3 L0,6 z" fill="#8c98a6"/></marker></defs>')

    kasten(20, 30, 215, 96, "1. Positionen", [
        "adsb.fi und adsb.lol (ADS-B)",
        "Open Glider Network (FLARM)",
        "alle 5 s, Umkreis 15 NM",
    ], "#1565c0")
    kasten(20, 150, 215, 96, "2. Muster und Kennzeichen", [
        "ADS-B-Feld r und desc",
        "OGN Device Database",
        "sonst nur Hexcode",
    ], "#2e7d32")
    kasten(20, 270, 215, 110, "3. Ortslagen", [
        "OpenStreetMap, bebaute Flächen",
        "Unterbruch: Abgrenzung der",
        "Bürgerinitiative",
        "100-m-Raster, Entfernungsfeld",
    ], "#ef6c00")

    kasten(300, 90, 215, 110, "4. Luftfahrzeuggruppe", [
        "DIN 45684-1: P 1.0 bis S",
        "Antrieb und Startmasse",
        "unbekanntes Muster wird",
        "getrennt ausgewiesen",
    ], "#6a1b9a")
    kasten(300, 230, 215, 110, "5. Pegelabschätzung", [
        "Bezugspegel in 300 m",
        "Abstandsmaß und Luftdämpfung",
        "über die Schrägentfernung",
        "Platzrunde: Zusatzpegel",
    ], "#00838f")

    kasten(580, 160, 215, 110, "6. Ergebnis", [
        "Ereignisse ab 55 dB(A)",
        "Ereignisse ab 65 dB(A)",
        "je Ortslage und Gruppe",
        "Karte, Tabelle, CSV",
    ], "#c2185b")

    pfeil(235, 78, 298, 120)
    pfeil(235, 198, 298, 160)
    pfeil(235, 320, 298, 290)
    pfeil(407, 200, 407, 228)
    pfeil(515, 285, 578, 230)

    s.append(f'<text x="{B/2:.0f}" y="{H-14}" font-size="11.5" '
             f'text-anchor="middle" fill="#7a8694">Jeder Schritt ist '
             f'nachvollziehbar; Schritt 5 ist eine Abschätzung, keine '
             f'Messung.</text>')
    s.append('</svg>')
    schreiben("erfassungskette.svg", "\n".join(s))


def schreiben(name, inhalt):
    pfad = os.path.join(ZIEL, name)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt + "\n")
    print(f"  {os.path.relpath(pfad, os.path.dirname(HIER))}  "
          f"({len(inhalt)//1024} kB)")


if __name__ == "__main__":
    print("Abbildungen erzeugt:")
    pegel_entfernung()
    erfassungskette()
