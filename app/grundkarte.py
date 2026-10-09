#!/usr/bin/env python3
"""Laedt einmalig einen Kartenhintergrund und legt ihn im Profil ab.

Die Auswertung soll ohne Internet funktionieren -- sie wird weitergegeben,
archiviert und soll in fuenf Jahren noch dieselbe Karte zeigen. Deshalb
werden die Kartenkacheln einmal heruntergeladen und direkt in die
Profildatei eingebettet, statt sie beim Ansehen nachzuladen.

    python3 grundkarte.py             fuer den eingestellten Platz
    python3 grundkarte.py --zoom 13   feiner, aber viermal so gross

Die Zoomstufe wird sonst so gewaehlt, dass die Kachelaufloesung zur
Kartengroesse passt -- feiner waere nur groesser, nicht schaerfer.

Datenquelle: OpenStreetMap, Lizenz ODbL, (c) OpenStreetMap-Mitwirkende.
Es werden einmalig wenige Dutzend Kacheln geladen; das bewegt sich im
Rahmen der Nutzungsbedingungen fuer Einzelanwendungen.
"""
import base64, json, math, os, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profil

UA = "Flugspur/1.0 (Buergerinitiative Fluglaerm; nicht-kommerziell; " \
     "Kontakt ueber github.com Projekt Flugspur)"
URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def kachel(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    la = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(la)) / math.pi) / 2.0 * n)
    return x, y


def kachel_ecken(x, y, z):
    """Liefert (lat_oben, lon_links, lat_unten, lon_rechts) einer Kachel."""
    n = 2.0 ** z

    def lat(yy):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))
    return lat(y), x / n * 360.0 - 180.0, lat(y + 1), (x + 1) / n * 360.0 - 180.0


def passende_zoomstufe(lat, view_km, px):
    """Zoomstufe, deren Aufloesung der Kartengroesse entspricht."""
    ziel = view_km * 2 * 1000 / px                      # Meter je Bildpunkt
    beste, bestd = 12, 1e9
    for z in range(9, 17):
        aufl = 156543.03392 * math.cos(math.radians(lat)) / (2 ** z)
        if abs(aufl - ziel) < bestd:
            beste, bestd = z, abs(aufl - ziel)
    return beste


def main():
    P = profil.lade()
    view = P["view_km"]
    px = 900
    z = 0
    if "--zoom" in sys.argv:
        z = int(sys.argv[sys.argv.index("--zoom") + 1])
    if not z:
        z = passende_zoomstufe(P["lat"], view, px)

    kla, klo = profil.km_pro_grad(P["lat"])
    dlat, dlon = view / kla, view / klo
    x1, y1 = kachel(P["lat"] + dlat, P["lon"] - dlon, z)
    x2, y2 = kachel(P["lat"] - dlat, P["lon"] + dlon, z)
    anzahl = (x2 - x1 + 1) * (y2 - y1 + 1)
    aufl = 156543.03392 * math.cos(math.radians(P["lat"])) / (2 ** z)

    print(f"Platz {P['code']} ({P['name']})")
    print(f"  Ausschnitt   {view*2:.0f} x {view*2:.0f} km")
    print(f"  Zoomstufe    {z}  ({aufl:.1f} m je Bildpunkt, "
          f"Karte zeigt {view*2*1000/px:.1f} m je Bildpunkt)")
    print(f"  Kacheln      {anzahl}")
    if anzahl > 120:
        print("  Das sind zu viele. Bitte kleinere Zoomstufe waehlen.")
        sys.exit(1)

    kacheln, fehler, bytes_ges = [], 0, 0
    for tx in range(x1, x2 + 1):
        for ty in range(y1, y2 + 1):
            url = URL.format(z=z, x=tx, y=ty)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=40) as r:
                    roh = r.read()
                o, l, u, re_ = kachel_ecken(tx, ty, z)
                kacheln.append({"n": round(o, 6), "w": round(l, 6),
                                "s": round(u, 6), "e": round(re_, 6),
                                "b64": base64.b64encode(roh).decode()})
                bytes_ges += len(roh)
            except Exception as e:
                fehler += 1
                print(f"  Kachel {z}/{tx}/{ty} nicht geladen: {e}")
            time.sleep(0.12)      # hoeflich bleiben

    if not kacheln:
        print("Keine Kachel geladen -- Abbruch.")
        sys.exit(1)

    ziel = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "plaetze", f"grundkarte_{P['code'].lower()}.json")
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump({"platz": P["code"], "zoom": z,
                   "erstellt": time.strftime("%Y-%m-%d"),
                   "quelle": "OpenStreetMap",
                   "hinweis": "(c) OpenStreetMap-Mitwirkende, Lizenz ODbL. "
                              "Kacheln eingebettet, damit die Auswertung "
                              "ohne Internet funktioniert.",
                   "kacheln": kacheln}, f)
    print(f"\n  {len(kacheln)} Kacheln geladen, {fehler} Fehler")
    print(f"  Geschrieben: {ziel} ({os.path.getsize(ziel)/1e6:.2f} MB)")
    print(f"  Die Auswertung waechst dadurch um rund "
          f"{bytes_ges*1.37/1e6:.1f} MB je Datei.")


if __name__ == "__main__":
    main()
