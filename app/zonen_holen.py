#!/usr/bin/env python3
"""Holt echte Ortsumrisse aus OpenStreetMap und legt sie dauerhaft ab.

Bisher war jede Ortslage ein Punkt mit einem Umkreis. Das ist aus zwei
Gruenden ungenau: Ein Ort ist keine Scheibe, und die Punkte im Profil
sassen teilweise mehrere Kilometer daneben.

Dieses Werkzeug laedt die tatsaechlich bebauten Flaechen in einem Zug,
ordnet jede Flaeche der naechstgelegenen Ortslage zu -- dadurch
ueberschneiden sich die Zonen nicht und nichts wird doppelt gezaehlt --
und schreibt das Ergebnis als Polygonzuege in eine Datei.

    python3 zonen_holen.py            holen und schreiben
    python3 zonen_holen.py --pruefen  nur vergleichen, nichts schreiben

Einmal ausfuehren; danach arbeitet die Auswertung offline weiter.
Datenquelle: OpenStreetMap, Lizenz ODbL, (c) OpenStreetMap-Mitwirkende.
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profil

UA = "Flugspur/1.0 (Buergerinitiative Fluglaerm; nicht-kommerziell)"
SERVER = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]
MAX_ZUORDNUNG_KM = 2.0      # weiter entfernte Flaechen gehoeren zu keinem Ort


def frage(q, versuche=4):
    letzter = None
    for runde in range(versuche):
        for url in SERVER:
            try:
                req = urllib.request.Request(
                    url, data=urllib.parse.urlencode({"data": q}).encode(),
                    headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)
            except Exception as e:
                letzter = f"{url.split('/')[2]} {type(e).__name__}"
                time.sleep(3 + runde * 4)
    raise RuntimeError(f"Overpass nicht erreichbar ({letzter})")


def flaeche_km2(ring):
    if len(ring) < 3:
        return 0.0
    la0 = sum(p[0] for p in ring) / len(ring)
    kla, klo = profil.km_pro_grad(la0)
    s = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][1] * klo, ring[i][0] * kla
        x2, y2 = ring[(i + 1) % len(ring)][1] * klo, ring[(i + 1) % len(ring)][0] * kla
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def mitte(ring):
    return (sum(p[0] for p in ring) / len(ring),
            sum(p[1] for p in ring) / len(ring))


def vereinfachen(ring, toleranz_m=20):
    """Douglas-Peucker, damit die Datei klein bleibt."""
    if len(ring) < 5:
        return ring
    kla, klo = profil.km_pro_grad(ring[0][0])

    def abst(p, a, b):
        px, py = p[1] * klo, p[0] * kla
        ax, ay = a[1] * klo, a[0] * kla
        bx, by = b[1] * klo, b[0] * kla
        dx, dy = bx - ax, by - ay
        if dx == dy == 0:
            return math.hypot(px - ax, py - ay) * 1000
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) * 1000

    def dp(pts):
        if len(pts) < 3:
            return pts
        wmax, idx = 0, 0
        for i in range(1, len(pts) - 1):
            w = abst(pts[i], pts[0], pts[-1])
            if w > wmax:
                wmax, idx = w, i
        if wmax > toleranz_m:
            return dp(pts[:idx + 1])[:-1] + dp(pts[idx:])
        return [pts[0], pts[-1]]

    out = dp(ring)
    return out if len(out) >= 4 else ring


def ortskerne(P):
    """Sucht fuer jede Ortslage den OSM-Knoten. Liefert korrigierte Punkte."""
    kerne = {}
    for name, la, lo in P["orte"]:
        teil = re.sub(r"\(.*?\)", "", name.split("-")[-1])
        begriffe = [t.strip() for t in teil.split("/") if t.strip()][::-1]
        treffer = None
        for b in begriffe:
            try:
                d = frage(f'[out:json][timeout:90];'
                          f'node["name"="{b}"](around:6000,{la},{lo});out body;')
            except Exception as e:
                print(f"  {name}: {e}")
                continue
            kand = [e for e in d.get("elements", []) if e.get("tags", {}).get("place")]
            kand = kand or d.get("elements", [])
            if kand:
                kand.sort(key=lambda e: profil.hav_km(la, lo, e["lat"], e["lon"]))
                e = kand[0]
                treffer = (e["lat"], e["lon"], e.get("tags", {}).get("place", "?"), b)
                break
        if treffer:
            kerne[name] = treffer
            v = profil.hav_km(la, lo, treffer[0], treffer[1])
            hinw = "   <<< Profilpunkt war falsch" if v > 1.0 else ""
            print(f"  {name:30s} {treffer[3]:14s} {treffer[2]:13s} "
                  f"Versatz {v:4.1f} km{hinw}")
        else:
            kerne[name] = (la, lo, "Profil", "")
            print(f"  {name:30s} nicht in OSM gefunden -- Profilpunkt bleibt")
        time.sleep(1.0)
    return kerne


def main():
    P = profil.lade()
    nur_pruefen = "--pruefen" in sys.argv
    ziel = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "plaetze", f"zonen_{P['code'].lower()}.json")

    print(f"Platz {P['code']} ({P['name']}) -- {len(P['orte'])} Ortslagen")
    print("Datenquelle: OpenStreetMap (ODbL)\n")
    print("Schritt 1 von 3: Ortslagen in OSM suchen")
    kerne = ortskerne(P)

    print(f"\nSchritt 2 von 3: bebaute Flaechen je Ortslage holen")
    roh, gesehen = [], set()
    for name, (kla, klo, _, _) in kerne.items():
        try:
            d = frage(f'[out:json][timeout:90];'
                      f'way["landuse"~"residential|retail"]'
                      f'(around:2500,{kla},{klo});out geom;')
        except Exception as e:
            print(f"  {name}: {e}")
            continue
        n = 0
        for e in d.get("elements", []):
            if e.get("id") in gesehen or not e.get("geometry"):
                continue
            gesehen.add(e["id"])
            ring = [(p["lat"], p["lon"]) for p in e["geometry"]]
            if flaeche_km2(ring) >= 0.015:
                roh.append(ring)
                n += 1
        print(f"  {name:30s} {n:3d} neue Flaechen")
        time.sleep(1.2)
    print(f"  insgesamt {len(roh)} Flaechen ab 1,5 ha")

    print("\nSchritt 3 von 3: jede Flaeche der naechsten Ortslage zuordnen")
    zuord = {n: [] for n in kerne}
    verworfen = 0
    for ring in roh:
        mla, mlo = mitte(ring)
        beste, bestd = None, 1e9
        for n, (kla, klo, _, _) in kerne.items():
            dd = profil.hav_km(kla, klo, mla, mlo)
            if dd < bestd:
                beste, bestd = n, dd
        if bestd <= MAX_ZUORDNUNG_KM:
            zuord[beste].append(ring)
        else:
            verworfen += 1

    ergebnis = {}
    for name, (kla, klo, typ, _) in kerne.items():
        ringe = [vereinfachen(r) for r in zuord[name]]
        ringe.sort(key=flaeche_km2, reverse=True)
        fl = sum(flaeche_km2(r) for r in ringe)
        if ringe:
            # Schwerpunkt flaechengewichtet
            sla = sum(mitte(r)[0] * flaeche_km2(r) for r in ringe) / fl
            slo = sum(mitte(r)[1] * flaeche_km2(r) for r in ringe) / fl
        else:
            sla, slo = kla, klo
        print(f"  {name:30s} {len(ringe):3d} Flaechen  {fl:5.2f} km2")
        ergebnis[name] = {
            "lat": round(sla, 5), "lon": round(slo, 5),
            "osm_punkt": [round(kla, 5), round(klo, 5)],
            "osm_typ": typ, "flaeche_km2": round(fl, 2),
            "ringe": [[[round(a, 5), round(b, 5)] for a, b in r] for r in ringe],
        }
    print(f"  ({verworfen} Flaechen keiner Ortslage zugeordnet, "
          f"weiter als {MAX_ZUORDNUNG_KM:g} km entfernt)")

    if nur_pruefen:
        print("\n--pruefen: nichts geschrieben.")
        return
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump({"platz": P["code"],
                   "hinweis": "Ortsumrisse aus OpenStreetMap, Lizenz ODbL, "
                              "(c) OpenStreetMap-Mitwirkende. Jede bebaute "
                              "Flaeche ist der naechstgelegenen Ortslage "
                              "zugeordnet, daher ueberschneidungsfrei.",
                   "erstellt": time.strftime("%Y-%m-%d"),
                   "orte": ergebnis}, f, ensure_ascii=False, indent=1)
    print(f"\nGeschrieben: {ziel} ({os.path.getsize(ziel)/1024:.0f} kB)")


if __name__ == "__main__":
    main()
