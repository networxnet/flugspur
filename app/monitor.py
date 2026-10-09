#!/usr/bin/env python3
"""Live-Monitor: zeigt im Browser, was gerade hereinkommt.

Startet einen kleinen Webserver (nur Standardbibliothek, keine Pakete).
Die Seite aktualisiert sich alle 10 Sekunden von selbst.

    python3 /app/monitor.py            Port 8099
    python3 /app/monitor.py --konsole  stattdessen Textausgabe im Terminal

Im Browser:  http://<NAS-Adresse>:8099
"""
import json, os, sys, time, glob, html, socket
from collections import defaultdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import subprocess, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profil, kennzeichen

P = profil.lade()
DATA = profil._env("DATA_DIR") or "/data"
PORT = int(profil._env("MONITOR_PORT") or 8099)
LOW_FT = P["low_ft"]
OVER_KM = P["overflight_km"]

def _ogn_id(r):
    k = r.get("icao")
    if k:
        return k.lower()
    i = r.get("id") or ""
    if i.startswith("ICA") and len(i) == 9:
        return i[3:].lower()
    return i

def heute():
    return datetime.now().strftime("%Y-%m-%d")

_CACHE = {}
_NAMEN = {"zeit": 0, "obj": None}

def namen():
    """Kennzeichenauflösung, hoechstens alle 5 Minuten neu einlesen."""
    if _NAMEN["obj"] is None or time.time() - _NAMEN["zeit"] > 300:
        try:
            _NAMEN["obj"] = kennzeichen.Namen(DATA)
        except Exception:
            _NAMEN["obj"] = _NAMEN["obj"] or kennzeichen.Namen("/tmp")
        _NAMEN["zeit"] = time.time()
    return _NAMEN["obj"]

def lies(tag):
    """Liest den Tag und liefert vereinheitlichte Punkte (mit Zwischenspeicher)."""
    sig = tuple((os.path.getmtime(f), os.path.getsize(f))
                for f in sorted(glob.glob(os.path.join(DATA, f"*_{tag}.ndjson"))))
    if _CACHE.get("sig") == sig:
        return _CACHE["pts"]
    pts = []
    for art, pfad in (("ADSB", os.path.join(DATA, f"adsb_{tag}.ndjson")),
                      ("OGN",  os.path.join(DATA, f"ogn_{tag}.ndjson"))):
        if not os.path.exists(pfad):
            continue
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for z in f:
                z = z.strip()
                if not z:
                    continue
                try:
                    r = json.loads(z)
                except json.JSONDecodeError:
                    continue
                N = namen()
                if art == "OGN":
                    pts.append({"t": r.get("ts"), "id": _ogn_id(r), "q": "OGN",
                                "lat": r.get("lat"), "lon": r.get("lon"),
                                "alt": r.get("alt_ft"),
                                "desc": N.muster(hexid=r.get("icao"),
                                                 ogn_id=r.get("id"),
                                                 desc=r.get("typ")),
                                "kz": N.anzeige(hexid=r.get("icao"),
                                                ogn_id=r.get("id"),
                                                reg=r.get("reg")),
                                "kt": r.get("kt")})
                else:
                    N.lerne(r.get("icao"), r.get("reg"),
                            r.get("type"), r.get("desc"))
                    pts.append({"t": r.get("t"), "id": r.get("icao"), "q": "ADSB",
                                "lat": r.get("lat"), "lon": r.get("lon"),
                                "alt": r.get("alt_ft"),
                                "desc": r.get("desc") or r.get("type"),
                                "kz": N.anzeige(hexid=r.get("icao"),
                                                reg=r.get("reg")),
                                "kt": r.get("gs_kt")})
    pts = [p for p in pts if p["t"] and p["id"] and p["lat"] is not None]
    pts.sort(key=lambda p: p["t"])
    _CACHE["sig"], _CACHE["pts"] = sig, pts
    return pts

def herzschlag(name):
    pfad = os.path.join(DATA, f"_heartbeat_{name}.txt")
    if not os.path.exists(pfad):
        return None, "noch keine Datei"
    try:
        zeilen = open(pfad).read().splitlines()
        alter = time.time() - int(zeilen[0])
        rest = " | ".join(z for z in zeilen[2:] if z)
        return alter, rest
    except Exception as e:
        return None, f"unlesbar: {e}"

def zustand():
    tag = heute()
    pts = lies(tag)
    jetzt = time.time()
    letzte5 = [p for p in pts if jetzt - p["t"] <= 300]
    letzte60 = [p for p in pts if jetzt - p["t"] <= 3600]

    # aktuell sichtbare Maschinen. Rollende und abgestellte Maschinen auf
    # dem Vorfeld in Duesseldorf senden weiter -- sie fliegen aber nicht.
    def am_boden(p):
        a, k = p.get("alt"), p.get("kt")
        if a is not None and a <= 0:
            return True
        return a is not None and a < 500 and k is not None and k < 40

    aktuell = {}
    for p in pts:
        if jetzt - p["t"] <= 120 and not am_boden(p):
            aktuell[p["id"]] = p

    # Ueberflüge heute, getrennt nach tief und gesamt
    ueber = defaultdict(lambda: [0, 0])   # [tief, gesamt]
    for name, ola, olo in P["orte"]:
        zuletzt = {}
        for p in pts:
            if profil.hav_km(ola, olo, p["lat"], p["lon"]) <= OVER_KM:
                v = zuletzt.get(p["id"])
                if v is None or p["t"] - v > 180:
                    ueber[name][1] += 1
                    if p["alt"] is not None and p["alt"] <= LOW_FT:
                        ueber[name][0] += 1
                zuletzt[p["id"]] = p["t"]

    dateien = []
    for mus in (f"adsb_{tag}.ndjson", f"ogn_{tag}.ndjson"):
        pf = os.path.join(DATA, mus)
        dateien.append((mus, os.path.getsize(pf) if os.path.exists(pf) else None))

    gesamt_mb = sum(os.path.getsize(f) for f in glob.glob(os.path.join(DATA, "*.ndjson"))) / 1e6
    tage = len({os.path.basename(f).rsplit("_", 1)[1][:10]
                for f in glob.glob(os.path.join(DATA, "*_????-??-??.ndjson"))})

    return dict(tag=tag, pts=pts, letzte5=letzte5, letzte60=letzte60,
                aktuell=aktuell, ueber=ueber, dateien=dateien,
                gesamt_mb=gesamt_mb, tage=tage,
                hb_adsb=herzschlag("adsb"), hb_ogn=herzschlag("ogn"))

def ampel(alter):
    if alter is None:
        return "#b3261e", "keine Daten"
    if alter < 90:
        return "#1e7a34", f"vor {alter:.0f} s"
    if alter < 300:
        return "#b8860b", f"vor {alter/60:.1f} min"
    return "#b3261e", f"seit {alter/60:.0f} min still"

def seite():
    z = zustand()
    e = html.escape
    fa, ta = ampel(z["hb_adsb"][0])
    fo, to = ampel(z["hb_ogn"][0])

    reihen = []
    for p in sorted(z["aktuell"].values(), key=lambda x: -x["t"])[:20]:
        tief = p["alt"] is not None and p["alt"] <= LOW_FT
        d = profil.hav_km(P["lat"], P["lon"], p["lat"], p["lon"])
        reihen.append(
            f"<tr{' style=background:#fff3f0' if tief else ''}>"
            f"<td><b>{e(p.get('kz') or p['id'])}</b>"
            f"<div style='font-size:10px;color:#9aa4b0'><code>{e(p['id'])}</code></div></td>"
            f"<td>{e(p['desc'] or '-')}</td>"
            f"<td align=right>{p['alt'] if p['alt'] is not None else '-'}</td>"
            f"<td align=right>{int(p['kt']) if p['kt'] else '-'}</td>"
            f"<td align=right>{d:.1f}</td>"
            f"<td>{e(p['q'])}</td>"
            f"<td>{datetime.fromtimestamp(p['t']):%H:%M:%S}</td></tr>")
    if not reihen:
        reihen = ['<tr><td colspan=7 style="color:#777;padding:14px">'
                  'Gerade nichts in der Luft (oder letzte Meldung älter als 2 Minuten).</td></tr>']

    orte = "<tr><th>Ortslage</th><th align=right>tief</th>" \
           "<th align=right>gesamt</th></tr>" + "".join(
        f"<tr><td>{e(n)}</td>"
        f"<td align=right><b style='color:{'#b3261e' if z['ueber'].get(n,[0,0])[0] else '#1b2430'}'>"
        f"{z['ueber'].get(n,[0,0])[0]}</b></td>"
        f"<td align=right style='color:#5a6673'>{z['ueber'].get(n,[0,0])[1]}</td></tr>"
        for n, _, _ in P["orte"])

    dat = "".join(
        f"<tr><td><code>{e(n)}</code></td><td align=right>"
        f"{'fehlt' if g is None else f'{g/1000:.0f} kB'}</td></tr>"
        for n, g in z["dateien"])

    tage = verfuegbare_tage()
    heut = heute()
    gestern = (datetime.fromtimestamp(time.time() - 86400)).strftime("%Y-%m-%d")
    def gruppe(beschriftung, ziel):
        return (f'<span class=gr><span class=gl>{beschriftung}</span>'
                f'<a class=btn href="/karte?tag={ziel}">'
                f'<span class=ic>&#9992;</span>Karte</a>'
                f'<a class=btn2 href="/text?tag={ziel}">'
                f'<span class=ic>&#9776;</span>Text</a></span>')

    knopf = []
    for bez, t in [("heute", heut), ("gestern", gestern)]:
        if t in tage:
            knopf.append(gruppe(bez, t))
    if len(tage) > 1:
        knopf.append(gruppe(f"alle {len(tage)} Tage", "alle"))
    knoepfe = ("".join(knopf) if knopf
               else '<span style="color:#777;font-size:13px">Noch keine '
                    'abgeschlossene Tagesdatei vorhanden.</span>')

    tief_jetzt = sum(1 for p in z["aktuell"].values()
                     if p["alt"] is not None and p["alt"] <= LOW_FT)

    return f"""<!DOCTYPE html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta http-equiv=refresh content=10>
<title>Flugspur Monitor {e(P['code'])}</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;
 padding:18px;background:#f4f6f8;color:#1b2430}}
.w{{max-width:1050px;margin:0 auto}}
h1{{font-size:21px;margin:0 0 2px}} .s{{color:#667;font-size:13px;margin-bottom:16px}}
.k{{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px}}
.c{{background:#fff;border:1px solid #e2e8ef;border-radius:9px;padding:13px 15px;
 flex:1 1 170px}}
.c b{{display:block;font-size:25px;line-height:1.2}} .c span{{font-size:12px;color:#5a6673}}
.box{{background:#fff;border:1px solid #e2e8ef;border-radius:9px;padding:0;
 margin-bottom:16px;overflow:hidden}}
.box h2{{font-size:14px;margin:0;padding:11px 15px;background:#f8fafc;
 border-bottom:1px solid #e9eef4;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td,th{{padding:6px 15px;border-bottom:1px solid #f0f3f7;text-align:left}}
th{{font-size:11px;text-transform:uppercase;color:#7a8694;font-weight:600}}
tr:last-child td{{border-bottom:none}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}}
.p{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}}
.z{{display:flex;gap:22px;padding:11px 15px;font-size:13px;flex-wrap:wrap}}
.aw{{display:flex;flex-wrap:wrap;gap:9px;padding:13px 15px}}
a.btn,a.btn2{{display:inline-flex;align-items:center;gap:7px;
 text-decoration:none;padding:9px 15px;border-radius:8px;font-size:13px;
 font-weight:500;line-height:1;border:1px solid transparent;
 transition:background .12s,border-color .12s}}
a.btn{{background:#1b2430;color:#fff}}
a.btn:hover{{background:#2c3a4d}}
a.btn2{{background:#fff;color:#33404f;border-color:#d4dce6}}
a.btn2:hover{{background:#f1f5f9;border-color:#b9c6d4}}
a.btn .ic,a.btn2 .ic{{font-size:14px;opacity:.85}}
.gr{{display:flex;align-items:center;gap:0;border-radius:8px;overflow:hidden;
 border:1px solid #d4dce6;background:#fff}}
.gr a{{border:0;border-radius:0;margin:0}}
.gr a+a{{border-left:1px solid #e3eaf1}}
.gl{{font-size:11px;text-transform:uppercase;letter-spacing:.04em;
 color:#7a8694;font-weight:600;padding:0 11px}}
.f{{text-align:center;color:#8a929c;font-size:11px;margin-top:8px}}
</style></head><body><div class=w>

<h1>Flugspur &middot; {e(P['name'])} ({e(P['code'])})</h1>
<div class=s>Stand {datetime.now():%d.%m.%Y %H:%M:%S} Uhr &middot;
 aktualisiert sich alle 10 Sekunden von selbst</div>

<div class=box><div class=z>
 <div><span class=p style="background:{fa}"></span><b>ADS-B</b> {ta}
   <span style="color:#778">{e(z['hb_adsb'][1])}</span></div>
 <div><span class=p style="background:{fo}"></span><b>OGN</b> {to}
   <span style="color:#778">{e(z['hb_ogn'][1])}</span></div>
</div></div>

<div class=k>
 <div class=c><b>{len(z['aktuell'])}</b><span>gerade in der Luft</span></div>
 <div class=c><b>{tief_jetzt}</b><span>davon tief (&le; {LOW_FT:.0f} ft)</span></div>
 <div class=c><b>{len(z['letzte5'])}</b><span>Meldungen letzte 5 Min</span></div>
 <div class=c><b>{len({p['id'] for p in z['letzte60']})}</b><span>Maschinen letzte Stunde</span></div>
 <div class=c><b>{len({p['id'] for p in z['pts']})}</b><span>Maschinen heute</span></div>
</div>

<div class=box><h2>Auswertung erzeugen</h2>
<div class=aw>{knoepfe}</div>
<div style="font-size:12px;color:#667;padding:0 15px 13px">Die Karte wird beim
Anklicken frisch aus den Mitschnitten berechnet — je nach Datenmenge
dauert das einige Sekunden. Sie öffnet sich in diesem Fenster; mit dem
Zurück-Knopf des Browsers kommen Sie hierher zurück.</div></div></div>

<div class=box><h2>Gerade in der Luft</h2>
<table><tr><th>Kennzeichen</th><th>Muster</th><th>ft</th><th>kt</th>
<th>km</th><th>Quelle</th><th>zuletzt</th></tr>
{''.join(reihen)}</table></div>

<div class=box><h2>Überflüge heute &middot; {OVER_KM:g} km Umkreis</h2>
<table>{orte}</table>
<div style="padding:9px 15px;font-size:12px;color:#667;border-top:1px solid #eef2f6">
<b>tief</b> = Durchgang in höchstens {LOW_FT:.0f} ft, lärmrelevant &middot;
<b>gesamt</b> = alle Höhen, enthält auch Düsseldorfer Verkehr in 5.000–7.000 ft.
Ein Ereignis je Luftfahrzeug und Durchgang.</div></div>

<div class=box><h2>Dateien</h2>
<table>{dat}
<tr><td>Gesamt über {z['tage']} Tag(e)</td>
<td align=right>{z['gesamt_mb']:.1f} MB</td></tr></table></div>

<div class=f>Nur Luftfahrzeuge mit ADS-B, MLAT-fähigem Mode&nbsp;S oder FLARM.
Alle Zahlen sind Untergrenzen.</div>
</div></body></html>"""

ARBEIT = tempfile.mkdtemp(prefix="flugspur-")
_LAUF = {}          # merkt sich laufende Auswertungen

def verfuegbare_tage():
    t = set()
    for f in glob.glob(os.path.join(DATA, "*_????-??-??.ndjson")):
        t.add(os.path.basename(f).rsplit("_", 1)[1][:10])
    return sorted(t)

def auswerten(skript, arg):
    """Ruft visualize.py oder summary.py auf. Schreibt nach ARBEIT,
    weil /data im Monitor absichtlich nur lesend eingebunden ist."""
    umg = dict(os.environ)
    umg["TRACKER_DATA_DIR"] = DATA
    umg["TRACKER_OUT_DIR"] = ARBEIT
    befehl = [sys.executable, os.path.join(os.path.dirname(
        os.path.abspath(__file__)), skript)]
    if arg:
        befehl.append(arg)
    r = subprocess.run(befehl, capture_output=True, text=True,
                       env=umg, timeout=600)
    return r.returncode, r.stdout, r.stderr

def rahmen(titel, inhalt, zurueck=True):
    return f"""<!DOCTYPE html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{html.escape(titel)}</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
margin:0;padding:18px;background:#f4f6f8;color:#1b2430}}
.w{{max-width:1050px;margin:0 auto}}
a.b{{display:inline-block;background:#1b2430;color:#fff;text-decoration:none;
padding:8px 14px;border-radius:7px;font-size:13px;margin-bottom:14px}}
pre{{background:#fff;border:1px solid #e2e8ef;border-radius:9px;padding:15px;
overflow:auto;font-size:12.5px;line-height:1.45}}</style></head><body><div class=w>
{'<a class=b href="/">&larr; zurück zum Monitor</a>' if zurueck else ''}
<h1 style="font-size:20px">{html.escape(titel)}</h1>
{inhalt}</div></body></html>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
      try:
        if self.path.startswith("/healthz"):
            self.send_response(200); self.send_header("Content-Type","text/plain")
            self.end_headers(); self.wfile.write(b"ok"); return
        weg = urlparse(self.path)
        frage = parse_qs(weg.query)
        tag = (frage.get("tag") or [None])[0]

        if weg.path == "/karte":
            code, aus, fehler = auswerten("visualize.py",
                                          "--all" if tag == "alle" else tag)
            datei = os.path.join(ARBEIT, "flugbewegungen_gesamt.html"
                                 if tag == "alle"
                                 else f"flugbewegungen_{tag}.html")
            if code == 0 and os.path.exists(datei):
                nutz = open(datei, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(nutz)))
                self.end_headers(); self.wfile.write(nutz); return
            nutz = rahmen("Grafische Auswertung nicht möglich",
                          "<pre>" + html.escape((aus or "") + (fehler or "")
                                                or "keine Ausgabe") + "</pre>").encode()
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(nutz)))
            self.end_headers(); self.wfile.write(nutz); return

        if weg.path == "/text":
            code, aus, fehler = auswerten("summary.py",
                                          "--all" if tag == "alle" else tag)
            nutz = rahmen(f"Textauswertung {tag or ''}".strip(),
                          "<pre>" + html.escape((aus or "") + (fehler or "")
                                                or "keine Ausgabe") + "</pre>").encode()
            self.send_response(200 if code == 0 else 500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(nutz)))
            self.end_headers(); self.wfile.write(nutz); return

        if self.path.startswith("/json"):
            z = zustand()
            nutz = json.dumps({
                "tag": z["tag"], "in_der_luft": len(z["aktuell"]),
                "meldungen_5min": len(z["letzte5"]),
                "maschinen_heute": len({p["id"] for p in z["pts"]}),
                "ueberfluege_tief": {k: v[0] for k, v in z["ueber"].items()},
                "ueberfluege_gesamt": {k: v[1] for k, v in z["ueber"].items()},
                "heartbeat_adsb_s": z["hb_adsb"][0],
                "heartbeat_ogn_s": z["hb_ogn"][0],
            }, ensure_ascii=False).encode()
            typ = "application/json; charset=utf-8"
        else:
            nutz = seite().encode("utf-8")
            typ = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(nutz)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(nutz)
      except Exception:
        import traceback
        txt = ("<!DOCTYPE html><meta charset=utf-8><title>Flugspur Monitor</title>"
               "<body style='font-family:sans-serif;padding:24px'>"
               "<h2>Der Monitor hat einen Fehler</h2><p>Bitte diesen Text melden:</p>"
               "<pre style='background:#f4f4f4;padding:14px;overflow:auto'>"
               + html.escape(traceback.format_exc()) + "</pre>").encode()
        try:
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(txt)))
            self.end_headers(); self.wfile.write(txt)
        except Exception:
            pass

    def log_message(self, *a):
        pass

def konsole():
    try:
        while True:
            z = zustand()
            os.system("clear" if os.name != "nt" else "cls")
            print(f"Flugspur {P['code']} -- {datetime.now():%H:%M:%S}")
            print("=" * 60)
            for nm, (al, rest) in (("ADS-B", z["hb_adsb"]), ("OGN  ", z["hb_ogn"])):
                print(f"  {nm}  {ampel(al)[1]:<18s} {rest}")
            print("-" * 60)
            print(f"  in der Luft: {len(z['aktuell']):3d} | "
                  f"Meldungen 5 Min: {len(z['letzte5']):5d} | "
                  f"heute: {len({p['id'] for p in z['pts']}):3d} Maschinen")
            print("-" * 60)
            for p in sorted(z["aktuell"].values(), key=lambda x: -x["t"])[:12]:
                d = profil.hav_km(P["lat"], P["lon"], p["lat"], p["lon"])
                print(f"  {p['id']:10s} {(p['desc'] or '-')[:22]:24s} "
                      f"{str(p['alt'] or '-'):>6s} ft {d:5.1f} km  {p['q']}")
            if not z["aktuell"]:
                print("  (gerade nichts in der Luft)")
            tief = {k: v[0] for k, v in z["ueber"].items() if v[0]}
            if tief:
                print("\n  Tiefe Ueberfluege heute: " +
                      ", ".join(f"{k} {v}" for k, v in sorted(tief.items())))
            print("\n  Abbruch mit Strg+C")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nBeendet.")

if __name__ == "__main__":
    if "--konsole" in sys.argv:
        konsole()
    else:
        srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
        try:
            name = socket.gethostname()
        except Exception:
            name = "NAS"
        print(f"Flugspur-Monitor laeuft auf Port {PORT}", flush=True)
        print(f"Im Browser oeffnen:  http://<Adresse-des-NAS>:{PORT}", flush=True)
        print(f"Datenverzeichnis: {DATA} | Platz: {P['code']} ({P['name']})", flush=True)
        try:
            dat = sorted(os.listdir(DATA))
            print(f"Gefundene Dateien in {DATA}: {len(dat)}", flush=True)
            for d in dat[:12]:
                print(f"   {d}", flush=True)
            if not dat:
                print("   HINWEIS: leer. Laufen die Logger und zeigen sie auf "
                      "dasselbe Verzeichnis?", flush=True)
        except Exception as ex:
            print(f"   FEHLER beim Lesen von {DATA}: {ex}", flush=True)
        print("Bereit. Jetzt im Browser oeffnen (http://, nicht https://).", flush=True)
        srv.serve_forever()
