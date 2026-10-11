#!/usr/bin/env python3
"""Selbsttest: prueft in einem Durchgang, ob die Installation vollstaendig
funktioniert -- Profil, Schreibrechte, beide Datenquellen, Auswertung,
Grafik.

Aufruf im Container:
    python3 /app/selbsttest.py

Dauer etwa 70 Sekunden. Am Ende steht ein klares BESTANDEN oder
FEHLGESCHLAGEN mit Begruendung. Erzeugte Testdateien werden wieder
geloescht; der laufende Mitschnitt wird nicht angetastet.
"""
import json, os, socket, subprocess, sys, tempfile, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OK, WARN, FAIL = "OK  ", "HINW", "FEHL"
ergebnisse = []

def melde(stufe, titel, text=""):
    ergebnisse.append((stufe, titel, text))
    marke = {OK: "[ OK ]", WARN: "[hinw]", FAIL: "[FEHL]"}[stufe]
    print(f"{marke} {titel}")
    if text:
        for zeile in text.splitlines():
            print(f"       {zeile}")

def kopf(t):
    print(f"\n--- {t} " + "-" * max(0, 56 - len(t)))

print("=" * 62)
print(" Flugspur -- Selbsttest")
print("=" * 62)

# ------------------------------------------------------------ 1. Profil
kopf("1. Profil")
try:
    import profil
    P = profil.lade()
    melde(OK, f"Profil geladen: {P['code']} -- {P['name']}",
          f"Lage {P['lat']}, {P['lon']} | Radius {P['radius_nm']} NM | "
          f"unter {P['max_alt_ft']:.0f} ft | Takt {P['interval_s']} s")
    if not P["orte"]:
        melde(WARN, "Keine Ortslagen im Profil",
              "Ueberflugauswertung bleibt leer. Orte in der Profildatei ergaenzen.")
    else:
        fern = [(n, profil.hav_km(P["lat"], P["lon"], la, lo))
                for n, la, lo in P["orte"]]
        weit = [f"{n} ({d:.0f} km)" for n, d in fern if d > 30]
        if weit:
            melde(WARN, "Ortslage sehr weit entfernt -- Zahlendreher?",
                  ", ".join(weit))
        else:
            melde(OK, f"{len(P['orte'])} Ortslagen, alle plausibel "
                      f"({min(d for _, d in fern):.1f}-{max(d for _, d in fern):.1f} km)")
    if not P["runways"]:
        melde(WARN, "Keine Pisten im Profil", "Betriebsrichtung wird nicht ermittelt.")
except SystemExit as e:
    melde(FAIL, "Profil konnte nicht geladen werden", str(e)); P = None
except Exception as e:
    melde(FAIL, "Profil konnte nicht geladen werden", f"{type(e).__name__}: {e}"); P = None

if P is None:
    print("\nAbbruch: ohne Profil sind die weiteren Tests sinnlos.")
    sys.exit(1)

# ------------------------------------------------------- 2. Schreibrechte
kopf("2. Datenverzeichnis")
DATA = profil._env("DATA_DIR") or "/data"
try:
    os.makedirs(DATA, exist_ok=True)
    pruef = os.path.join(DATA, "_selbsttest.tmp")
    with open(pruef, "w") as f:
        f.write("x")
    os.remove(pruef)
    melde(OK, f"Schreiben in {DATA} moeglich", f"als Benutzer {os.getuid()}:{os.getgid()}")
except Exception as e:
    melde(FAIL, f"Kein Schreibrecht auf {DATA}",
          f"{type(e).__name__}: {e}\n"
          f"Abhilfe: Ordnerrechte setzen oder in der Compose-Datei "
          f'user: "0:0" ergaenzen.')

# --------------------------------------------------------- 3. ADS-B-Netze
kopf("3. ADS-B-Quellen")
erreichbar = 0
for name, url in [
    ("adsb.fi",  f"https://opendata.adsb.fi/api/v2/lat/{P['lat']:.4f}/lon/{P['lon']:.4f}/dist/{P['radius_nm']:.0f}"),
    ("adsb.lol", f"https://api.adsb.lol/v2/lat/{P['lat']:.4f}/lon/{P['lon']:.4f}/dist/{P['radius_nm']:.0f}"),
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Flugspur/1.0 (Selbsttest)"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        n = len(d.get("ac") or d.get("aircraft") or [])
        melde(OK, f"{name} erreichbar", f"{n} Ziele gemeldet, Antwort in {time.time()-t0:.1f} s")
        erreichbar += 1
    except Exception as e:
        melde(WARN, f"{name} nicht erreichbar", f"{type(e).__name__}: {e}")
if erreichbar == 0:
    melde(FAIL, "Keine einzige ADS-B-Quelle erreichbar",
          "Internetzugang des Containers pruefen (DNS, Firewall).")

# ------------------------------------------------------------- 4. OGN
kopf("4. OGN-Netz (Segelflug, Ultraleicht)")
try:
    s = socket.create_connection(("aprs.glidernet.org", 14580), timeout=20)
    s.sendall(b"user FSTEST pass -1 vers flugspur-selbsttest 1.0 "
              + f"filter r/{P['lat']:.4f}/{P['lon']:.4f}/{P['radius_nm']*1.852:.0f}\n".encode())
    s.settimeout(25)
    roh, zeilen = b"", 0
    ende = time.time() + 25
    while time.time() < ende and zeilen < 3:
        try:
            teil = s.recv(4096)
        except socket.timeout:
            break
        if not teil:
            break
        roh += teil
        zeilen = sum(1 for z in roh.split(b"\n")
                     if z.strip() and not z.startswith(b"#"))
    s.close()
    if zeilen:
        melde(OK, "OGN-Netz liefert Daten", f"{zeilen} Positionsmeldungen in 25 s")
    else:
        melde(WARN, "OGN verbunden, aber keine Positionen",
              "Entweder fliegt gerade nichts, oder es steht kein OGN-Empfaenger\n"
              "in Reichweite. Abdeckung pruefen: http://ognrange.onglide.com/\n"
              "ADS-B funktioniert davon unabhaengig.")
except Exception as e:
    melde(WARN, "OGN-Netz nicht erreichbar",
          f"{type(e).__name__}: {e}\n"
          f"Haeufigste Ursache: ausgehender Port 14580 von der NAS-Firewall\n"
          f"blockiert. Ohne OGN fehlen Segelflug und Ultraleicht.")

# ------------------------------------- 5. Mitschnitt und Auswertung real
kopf("5. Durchgaengiger Probelauf (etwa 40 s)")
tmp = tempfile.mkdtemp(prefix="flugspur_test_")
APP = os.path.dirname(os.path.abspath(__file__))
umg = dict(os.environ, TRACKER_DATA_DIR=tmp, TRACKER_OUT_DIR=tmp,
           TRACKER_INTERVAL_S="3")
try:
    p = subprocess.Popen([sys.executable, os.path.join(APP, "adsb_logger.py")],
                         env=umg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(40)
    p.terminate()
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()

    dateien = [f for f in os.listdir(tmp) if f.endswith(".ndjson")]
    pos = sum(sum(1 for _ in open(os.path.join(tmp, f))) for f in dateien)
    hb = os.path.join(tmp, "_heartbeat_adsb.txt")

    if not os.path.exists(hb):
        melde(FAIL, "Logger hat keinen Heartbeat geschrieben",
              "Der Mitschnitt laeuft nicht korrekt.")
    elif pos == 0:
        melde(WARN, "Logger laeuft, aber 0 Positionen erfasst",
              "Das ist nachts und bei schlechtem Wetter normal.\n"
              "Zur Gegenprobe tagsueber wiederholen oder voruebergehend\n"
              "TRACKER_MAX_ALT_FT hochsetzen (dann erscheint Durchgangsverkehr).")
    else:
        melde(OK, f"Mitschnitt funktioniert", f"{pos} Positionen in 40 s")

    # Auswertung
    r = subprocess.run([sys.executable, os.path.join(APP, "summary.py")],
                       env=umg, capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and ("Mitschnitt" in r.stdout or "Keine Daten" in r.stdout):
        melde(OK, "Auswertung laeuft durch")
    else:
        melde(FAIL, "Auswertung fehlgeschlagen",
              (r.stderr or r.stdout)[-400:])

    # Grafik
    r = subprocess.run([sys.executable, os.path.join(APP, "visualize.py")],
                       env=umg, capture_output=True, text=True, timeout=120)
    htmls = [f for f in os.listdir(tmp) if f.endswith(".html")]
    if htmls:
        gr = os.path.getsize(os.path.join(tmp, htmls[0])) / 1024
        inhalt = open(os.path.join(tmp, htmls[0]), encoding="utf-8").read()
        extern = inhalt.count('src="http') + inhalt.count('href="http')
        melde(OK, "Grafische Auswertung erzeugt",
              f"{htmls[0]} ({gr:.0f} kB), {extern} externe Verweise "
              f"(0 = funktioniert offline)")
    elif r.returncode == 0:
        melde(WARN, "Keine Grafik erzeugt", "Mangels Daten -- siehe oben.")
    else:
        melde(FAIL, "Grafik fehlgeschlagen", (r.stderr or r.stdout)[-400:])
finally:
    for f in os.listdir(tmp):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass
    try:
        os.rmdir(tmp)
    except OSError:
        pass

# ------------------------------------------------- 6. Monitor startet
# Uebersetzen allein genuegt nicht: Ein fehlender Import faellt erst beim
# Ausfuehren auf. Deshalb wird der Monitor hier wirklich gestartet und
# ueber das Netz befragt.
kopf("6. Monitor startet und antwortet")
_port = int(os.environ.get("TRACKER_SELBSTTEST_PORT", "8098"))
_tmp2 = tempfile.mkdtemp()
_umg = dict(os.environ, TRACKER_DATA_DIR=_tmp2,
            TRACKER_MONITOR_PORT=str(_port))
_pr = subprocess.Popen([sys.executable, os.path.join(APP, "monitor.py")],
                       env=_umg, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
try:
    import urllib.request
    _ok = False
    for _ in range(25):
        time.sleep(1)
        if _pr.poll() is not None:
            break
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{_port}/healthz", timeout=3) as r:
                if r.status == 200:
                    _ok = True
                    break
        except Exception:
            pass
    if _pr.poll() is not None:
        _aus = (_pr.stdout.read() or "")[-500:]
        melde(FAIL, "Monitor beendet sich sofort", _aus.strip())
    elif not _ok:
        melde(FAIL, "Monitor antwortet nicht",
              f"Port {_port} liefert keine Antwort.")
    else:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{_port}/", timeout=15) as r:
                _gr = len(r.read())
            melde(OK, "Monitor startet und antwortet",
                  f"Startseite {_gr/1024:.0f} kB ueber Port {_port}")
        except Exception as e:
            melde(FAIL, "Monitor liefert keine Startseite", str(e))
finally:
    _pr.terminate()
    try:
        _pr.wait(timeout=10)
    except Exception:
        _pr.kill()
    for f in os.listdir(_tmp2):
        try:
            os.remove(os.path.join(_tmp2, f))
        except OSError:
            pass
    try:
        os.rmdir(_tmp2)
    except OSError:
        pass

# ------------------------------------------------------------- Fazit
print("\n" + "=" * 62)
f = sum(1 for s, _, _ in ergebnisse if s == FAIL)
w = sum(1 for s, _, _ in ergebnisse if s == WARN)
if f:
    print(f" FEHLGESCHLAGEN -- {f} Fehler, {w} Hinweise")
    print("\n Zu beheben:")
    for s, t, _ in ergebnisse:
        if s == FAIL:
            print(f"   - {t}")
    code = 1
elif w:
    print(f" BESTANDEN mit {w} Hinweis(en)")
    print("\n Beachten:")
    for s, t, _ in ergebnisse:
        if s == WARN:
            print(f"   - {t}")
    code = 0
else:
    print(" BESTANDEN -- alle Pruefungen fehlerfrei")
    code = 0
print("=" * 62)
sys.exit(code)
