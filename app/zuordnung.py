#!/usr/bin/env python3
"""Ordnet jede Flugspur dem Platz zu, zu dem sie gehoert.

Warum das noetig ist: Im Erfassungsradius von 15 NM liegt auch
Duesseldorf. Der weitaus groesste Teil der Meldungen stammt von dort und
hat mit dem Flugplatz Moenchengladbach nichts zu tun. Wer das nicht
trennt, schreibt Duesseldorfer Anflugverkehr den Anwohnern von Schiefbahn
zu -- und umgekehrt.

**Nicht geeignet ist das Luftfahrzeugmuster.** Geschaeftsreisejets fliegen
beide Plaetze an, und Kleinflugzeuge durchqueren den Nahbereich von
Duesseldorf. Am 10.10.2026 war eine Citation tief ueber Moenchengladbach
und eine Cessna 152 tief bei Duesseldorf.

**Auch das Rufzeichen taugt nicht als Filter.** Die Flugschule am Platz,
die RWL German Flight Academy, verwendet Rufzeichen im Stil einer
Fluggesellschaft (`RWL5545`). Ein Filter nach Rufzeichenform wuerde
ausgerechnet die Schulfluege aussortieren.

Zuverlaessig ist allein die **Flugbahn**: Wer tief und nah am Platz war,
gehoert dorthin.

Das Rufzeichen ist dafuer als **Betreibermerkmal** nuetzlich. Damit laesst
sich beziffern, welcher Anteil des Betriebs auf Flugschulen entfaellt --
eine Frage, die bei Buergerinitiativen regelmaessig gestellt und selten
belegt wird.

Aufruf:
    python3 /app/zuordnung.py                 alle Tage
    python3 /app/zuordnung.py --tag 2026-10-10
    python3 /app/zuordnung.py --tag 2026-10-10 --spuren
"""

import argparse
import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime

import profil
import laerm

DATA_DIR = os.environ.get("TRACKER_DATA_DIR", "/data")
_P = profil.lade()
hav_km = profil.hav_km

_Z = _P.get("zuordnung") or {}
NAH_KM = float(_Z.get("nah_km", 3.0))
TIEF_FT = float(_Z.get("tief_ft", 1500.0))
PR_UMKREIS_KM = float(_Z.get("platzrunde_umkreis_km", 6.0))
PR_MIND_DURCH = int(_Z.get("platzrunde_mind_durchgaenge", 3))
PR_MIND_MIN = int(_Z.get("platzrunde_mind_minuten", 8))
ENTPRELLUNG_S = 180

NACHBARN = _P.get("nachbarplaetze") or []

# Rufzeichen im Stil einer Fluggesellschaft: drei Buchstaben, dann Ziffer
RUF_GESELLSCHAFT = re.compile(r"^([A-Z]{3})\d")

# Bekannte Praefixe. Die Liste erhebt keinen Anspruch auf Vollstaendigkeit
# und soll es auch nicht -- was fehlt, erscheint unter seinem Praefix und
# kann hier ergaenzt werden.
BETREIBER = {
    "RWL": "RWL German Flight Academy (Flugschule, Heimatplatz EDLN)",
}


def laden(tag=None):
    muster = f"*_{tag}.ndjson" if tag else "*.ndjson"
    spuren = defaultdict(list)
    for pfad in sorted(glob.glob(os.path.join(DATA_DIR, muster))):
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    r = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                if r.get("lat") is None or r.get("lon") is None:
                    continue
                if r.get("net") == "OGN":
                    kid, t = r.get("id"), r.get("ts")
                    p = {"t": t, "lat": r["lat"], "lon": r["lon"],
                         "alt": r.get("alt_ft"), "call": None,
                         "typ": r.get("typ"), "desc": None,
                         "reg": r.get("reg"), "q": "OGN"}
                else:
                    kid, t = r.get("icao"), r.get("t")
                    p = {"t": t, "lat": r["lat"], "lon": r["lon"],
                         "alt": r.get("alt_ft"), "call": (r.get("call") or "").strip(),
                         "typ": r.get("type"), "desc": r.get("desc"),
                         "reg": r.get("reg"), "q": "ADSB"}
                if kid and t:
                    spuren[kid].append(p)
    for tr in spuren.values():
        tr.sort(key=lambda x: x["t"])
    return spuren


PAUSE_S = 1800          # groessere Luecke -> neuer Uebungsabschnitt


def _durchgaenge(tr, lat, lon, umkreis_km, tief_ft):
    """Tiefe Annaeherungen, Umlaufzeit und Dauer der Uebungsabschnitte.

    Wichtig ist die Trennung in Abschnitte: Wer vormittags und nachmittags
    uebt, hat nicht fuenf Stunden am Stueck Platzrunden geflogen. Gezaehlt
    wird deshalb je zusammenhaengendem Abschnitt, Pausen ueber einer halben
    Stunde trennen.
    """
    zeiten = []
    letzte = None
    for p in tr:
        if p["alt"] is None or p["alt"] > tief_ft:
            continue
        if hav_km(lat, lon, p["lat"], p["lon"]) > umkreis_km:
            continue
        if letzte is None or p["t"] - letzte > ENTPRELLUNG_S:
            zeiten.append(p["t"])
        letzte = p["t"]
    if not zeiten:
        return 0, 0.0, None

    # Abschnitte bilden
    abschnitte, akt = [], [zeiten[0]]
    for t in zeiten[1:]:
        if t - akt[-1] > PAUSE_S:
            abschnitte.append(akt)
            akt = [t]
        else:
            akt.append(t)
    abschnitte.append(akt)

    dauer = sum((a[-1] - a[0]) for a in abschnitte) / 60.0
    umlauf = [b - a for ab in abschnitte
              for a, b in zip(ab, ab[1:])]
    umlauf.sort()
    mitte = umlauf[len(umlauf) // 2] / 60.0 if umlauf else None
    return len(zeiten), dauer, mitte


def betreiber(call, reg):
    if call:
        m = RUF_GESELLSCHAFT.match(call.upper())
        if m:
            kurz = m.group(1)
            return BETREIBER.get(kurz, f"Rufzeichen {kurz}")
    if reg or call:
        return "Kennzeichen (privat, Verein oder Charter)"
    return "ohne Rufzeichen"


def einordnen(tr):
    """Liefert Klasse, Betreiber, Gruppe und ein paar Kennwerte."""
    lat, lon = _P["lat"], _P["lon"]
    call = next((p["call"] for p in tr if p.get("call")), "")
    reg = next((p["reg"] for p in tr if p.get("reg")), None)
    typ = next((p["typ"] for p in tr if p.get("typ")), None)
    desc = next((p["desc"] for p in tr if p.get("desc")), None)
    grp = laerm.gruppe(typ, desc)

    d_min = min(hav_km(lat, lon, p["lat"], p["lon"]) for p in tr)
    h_min = min((p["alt"] for p in tr if p["alt"] is not None), default=None)

    n_pr, dauer, umlauf = _durchgaenge(tr, lat, lon, PR_UMKREIS_KM, TIEF_FT)
    am_platz = any(p["alt"] is not None and p["alt"] <= TIEF_FT
                   and hav_km(lat, lon, p["lat"], p["lon"]) <= NAH_KM
                   for p in tr)

    if am_platz and n_pr >= PR_MIND_DURCH and dauer >= PR_MIND_MIN:
        klasse = "Platzrunde EDLN"
    elif am_platz:
        klasse = "Start oder Landung EDLN"
    else:
        klasse = None
        for n in NACHBARN:
            if any(p["alt"] is not None
                   and p["alt"] <= float(n.get("tief_ft", 2500))
                   and hav_km(n["lat"], n["lon"], p["lat"], p["lon"])
                   <= float(n.get("nah_km", 5.0)) for p in tr):
                klasse = f"Bewegung {n['name']}"
                break
        if klasse is None:
            klasse = "Durchgangsverkehr"

    return {"klasse": klasse, "betreiber": betreiber(call, reg),
            "gruppe": grp, "call": call, "reg": reg, "typ": typ,
            "d_min_km": d_min, "h_min_ft": h_min,
            "durchgaenge": n_pr, "dauer_min": dauer,
            "umlauf_min": umlauf,
            "meldungen": len(tr)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="YYYY-MM-DD, sonst alle Tage")
    ap.add_argument("--spuren", action="store_true",
                    help="jede Spur einzeln auflisten")
    a = ap.parse_args()

    spuren = laden(a.tag)
    if not spuren:
        print(f"Keine Daten in {DATA_DIR}"
              + (f" fuer {a.tag}" if a.tag else ""))
        return
    erg = {k: einordnen(tr) for k, tr in spuren.items()}

    print(f"Zuordnung der Flugspuren{' am ' + a.tag if a.tag else ''}")
    print(f"{len(erg)} Luftfahrzeuge\n")

    nach_klasse = defaultdict(list)
    for k, e in erg.items():
        nach_klasse[e["klasse"]].append(e)
    reihe = ["Platzrunde EDLN", "Start oder Landung EDLN"]
    reihe += sorted(x for x in nach_klasse if x.startswith("Bewegung "))
    reihe += ["Durchgangsverkehr"]
    print(f"  {'Klasse':30s} {'Anzahl':>7s}  Anteil")
    for kl in reihe:
        m = nach_klasse.get(kl, [])
        if not m:
            continue
        print(f"  {kl:30s} {len(m):7d}  {100*len(m)/len(erg):5.1f} %")

    edln = [e for e in erg.values() if e["klasse"].endswith("EDLN")]
    if not edln:
        print("\nKeine Bewegung mit Bezug zu EDLN erkannt.")
        return

    print(f"\n--- Nur die {len(edln)} Bewegungen mit Bezug zu EDLN ---\n")
    print("  Nach Luftfahrzeuggruppe:")
    g = defaultdict(int)
    for e in edln:
        g[laerm.KLARTEXT[e["gruppe"]]] += 1
    for n, c in sorted(g.items(), key=lambda x: -x[1]):
        print(f"    {n:26s} {c:4d}  {100*c/len(edln):5.1f} %")

    print("\n  Nach Betreiber (aus dem Rufzeichen):")
    b = defaultdict(int)
    for e in edln:
        b[e["betreiber"]] += 1
    for n, c in sorted(b.items(), key=lambda x: -x[1]):
        print(f"    {n[:46]:48s} {c:4d}  {100*c/len(edln):5.1f} %")

    pr = [e for e in edln if e["klasse"] == "Platzrunde EDLN"]
    if pr:
        d = sorted(e["dauer_min"] for e in pr)
        u = sorted(e["umlauf_min"] for e in pr if e["umlauf_min"])
        print(f"\n  Platzrunden: {len(pr)} Luftfahrzeuge, "
              f"zusammen {sum(e['durchgaenge'] for e in pr)} tiefe Durchgaenge")
        print(f"    Durchgaenge je Luftfahrzeug im Median: "
              f"{sorted(e['durchgaenge'] for e in pr)[len(pr)//2]}")
        print(f"    Uebungsdauer im Median {d[len(d)//2]:.0f} min, "
              f"laengste {d[-1]:.0f} min")
        if u:
            print(f"    Zeit zwischen zwei Durchgaengen im Median "
                  f"{u[len(u)//2]:.1f} min")

    print("\n  HINWEIS: Die Zuordnung beruht auf der Flugbahn, nicht auf")
    print("  Flugplandaten -- ADS-B uebertraegt weder Start noch Ziel.")
    print("  Luftfahrzeuge ohne Transponder fehlen vollstaendig.")

    if a.spuren:
        print(f"\n--- Einzelne Spuren ---\n")
        print(f"  {'Kennung':9s} {'Ruf':9s} {'Muster':6s} {'Klasse':26s} "
              f"{'naechst':>8s} {'tiefst':>7s} {'Durchg':>7s}")
        for k, e in sorted(erg.items(), key=lambda x: x[1]["d_min_km"]):
            if not e["klasse"].endswith("EDLN") and not a.tag:
                continue
            h = f"{e['h_min_ft']:.0f}" if e["h_min_ft"] is not None else "-"
            print(f"  {k:9s} {(e['call'] or '-')[:9]:9s} "
                  f"{(e['typ'] or '-')[:6]:6s} {e['klasse'][:26]:26s} "
                  f"{e['d_min_km']:7.1f}k {h:>7s} {e['durchgaenge']:7d}")


if __name__ == "__main__":
    main()
