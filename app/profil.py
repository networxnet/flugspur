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
import tempfile
import json, os, math

BASE = os.path.dirname(os.path.abspath(__file__))
PLATZ_DIR = os.path.join(BASE, "plaetze")

# Zusaetzliches Verzeichnis ausserhalb des Programmcodes. Gedacht fuer den
# Betrieb aus einem fertigen Abbild: Das Abbild bringt Profile mit, aber
# wer eine Schwelle aendern oder eine Ortsgrenze korrigieren will, legt
# die Datei hier ab -- ohne neues Abbild, ohne Neubau.
#
# Gesucht wird immer zuerst hier, dann im Abbild.
EXTERN_DIR = os.environ.get("FS_PROFIL_DIR") or os.environ.get(
    "TRACKER_PROFIL_DIR") or "/profil"


def profil_datei(name):
    """Pfad zu einer Profildatei: aussen vor innen."""
    aussen = os.path.join(EXTERN_DIR, name)
    if os.path.exists(aussen):
        return aussen
    return os.path.join(PLATZ_DIR, name)

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
    "laerm_schraeg_m": 1500.0,   # Rueckfall, wenn das Profil nichts sagt
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
        pfad = profil_datei(f"{code.strip().lower()}.json")

    if pfad:
        if not os.path.exists(pfad):
            raise SystemExit(
                f"Profil nicht gefunden: {pfad}\n"
                f"Verfuegbar: {', '.join(verfuegbare_plaetze()) or '(keine)'}\n"
                f"Setzen Sie TRACKER_PLATZ (Kuerzel) oder TRACKER_PROFIL (Pfad)."
            )
        with open(pfad, encoding="utf-8") as f:
            p.update(json.load(f))

    # Umgebungsvariablen haben das letzte Wort.
    # Geprueft werden ALLE Schluessel des wirksamen Profils, nicht nur die
    # eingebauten Vorgaben -- sonst liesse sich ein Wert, der erst im
    # Profil dazugekommen ist, nicht von aussen aendern.
    for k in list(p.keys()):
        if k in ("runways", "orte", "platzrunde_geometrie"):
            continue
        v = _env(k)
        if v is not None:
            p[k] = _cast(v, VORGABEN.get(k, p[k]))
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


# ---------------------------------------------------------------- Zonen

def _zonendatei(code):
    return profil_datei(f"zonen_{code.lower()}.json")


def lade_zonen(P):
    """Echte Ortsumrisse aus OpenStreetMap, falls vorhanden.

    Liefert {Ortsname: [Ring, ...]} mit Ring = [(lat, lon), ...].
    Fehlt die Datei, bleibt es beim Kreis um den Profilpunkt."""
    pfad = _zonendatei(P["code"])
    if not os.path.exists(pfad):
        return {}
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return {}
    raus = {}
    for name, e in d.get("orte", {}).items():
        ringe = [[(a, b) for a, b in r] for r in e.get("ringe", [])]
        if ringe:
            raus[name] = ringe
    return raus


def im_polygon(lat, lon, ring):
    """Strahlenverfahren: liegt der Punkt innerhalb des Polygonzugs?"""
    drin = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        yi, xi = ring[i]
        yj, xj = ring[j]
        if (yi > lat) != (yj > lat):
            schnitt = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < schnitt:
                drin = not drin
        j = i
    return drin


def in_zone(lat, lon, ringe):
    for r in ringe:
        if im_polygon(lat, lon, r):
            return True
    return False


def zonen_umgriff(ringe):
    """Grobes Rechteck um alle Ringe -- spart Rechenzeit bei vielen Punkten."""
    la = [p[0] for r in ringe for p in r]
    lo = [p[1] for r in ringe for p in r]
    return min(la), min(lo), max(la), max(lo)


# --------------------------------------------------- Laermrelevanz je Zone

class Zonenfeld:
    """Entfernungsfeld einer Ortslage.

    Liefert zu jedem Punkt die seitliche Entfernung zur bebauten Flaeche.
    Daraus und aus der Flughoehe ergibt sich die Schraegentfernung -- das
    Mass, das fuer die Laermbelastung zaehlt. Ein direkter Ueberflug ist
    dafuer nicht noetig: Eine tief fliegende Maschine 500 m daneben ist
    naeher als ein Verkehrsflugzeug senkrecht darueber in 7000 ft.

    Intern ein Raster von 100 m. Das genuegt: Die Positionsmeldungen
    selbst sind nicht genauer, und die Ortsgrenze ist ohnehin keine
    scharfe Linie.
    """

    ZELLE_M = 100.0
    MAX_M = 4000.0          # reicht bis zur 55-dB(A)-Schwelle eines Jets

    def __init__(self, ringe):
        self.ringe = ringe
        la = [p[0] for r in ringe for p in r]
        lo = [p[1] for r in ringe for p in r]
        rand = self.MAX_M / 1000.0
        self.kla, self.klo = km_pro_grad(sum(la) / len(la))
        self.la0 = min(la) - rand / self.kla
        self.lo0 = min(lo) - rand / self.klo
        self.nla = int((max(la) + rand / self.kla - self.la0)
                       * self.kla * 1000 / self.ZELLE_M) + 2
        self.nlo = int((max(lo) + rand / self.klo - self.lo0)
                       * self.klo * 1000 / self.ZELLE_M) + 2
        self._feld = self._bauen()

    def _zelle(self, lat, lon):
        return (int((lat - self.la0) * self.kla * 1000 / self.ZELLE_M),
                int((lon - self.lo0) * self.klo * 1000 / self.ZELLE_M))

    def _mitte(self, i, j):
        return (self.la0 + (i + 0.5) * self.ZELLE_M / 1000 / self.kla,
                self.lo0 + (j + 0.5) * self.ZELLE_M / 1000 / self.klo)

    def _bauen(self):
        """Breitensuche vom bebauten Gebiet nach aussen."""
        from collections import deque
        gross = 10 ** 9
        feld = [[gross] * self.nlo for _ in range(self.nla)]
        q = deque()
        for i in range(self.nla):
            for j in range(self.nlo):
                la, lo = self._mitte(i, j)
                if in_zone(la, lo, self.ringe):
                    feld[i][j] = 0
                    q.append((i, j))
        maxschritt = int(self.MAX_M / self.ZELLE_M)
        while q:
            i, j = q.popleft()
            if feld[i][j] >= maxschritt:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < self.nla and 0 <= b < self.nlo \
                        and feld[a][b] > feld[i][j] + 1:
                    feld[a][b] = feld[i][j] + 1
                    q.append((a, b))
        return feld

    def seitlich_m(self, lat, lon):
        """Seitliche Entfernung zur bebauten Flaeche in Metern."""
        i, j = self._zelle(lat, lon)
        if not (0 <= i < self.nla and 0 <= j < self.nlo):
            return self.MAX_M
        return min(self._feld[i][j] * self.ZELLE_M, self.MAX_M)

    def schraeg_m(self, lat, lon, alt_ft):
        """Schraegentfernung zur naechsten Bebauung in Metern."""
        import math as _m
        s = self.seitlich_m(lat, lon)
        h = (alt_ft or 0) * 0.3048
        return _m.hypot(s, h)

    def zellen(self):
        """Alle bebauten Zellen als (lat_unten, lon_links, lat_oben, lon_rechts)."""
        out = []
        for i in range(self.nla):
            j = 0
            while j < self.nlo:
                if self._feld[i][j] == 0:
                    k = j
                    while k < self.nlo and self._feld[i][k] == 0:
                        k += 1
                    u, l = self._mitte(i, j)
                    o, r = self._mitte(i, k - 1)
                    h = self.ZELLE_M / 1000 / self.kla / 2
                    b = self.ZELLE_M / 1000 / self.klo / 2
                    out.append((u - h, l - b, o + h, r + b))
                    j = k
                else:
                    j += 1
        return out


def _zonen_schluessel(P, z):
    """Kennzahl, die sich aendert, sobald das Feld neu gebaut werden muss."""
    import hashlib
    teile = [f"v2", f"{Zonenfeld.ZELLE_M}", f"{Zonenfeld.MAX_M}"]
    try:
        pfad = _zonendatei(P["code"])
        if pfad and os.path.exists(pfad):
            st = os.stat(pfad)
            teile.append(f"{st.st_size}:{int(st.st_mtime)}")
    except OSError:
        pass
    for n in sorted(z):
        teile.append(f"{n}:{sum(len(r) for r in z[n])}")
    return hashlib.sha256("|".join(teile).encode()).hexdigest()[:16]


def lade_zonenfelder(P, zonen=None):
    """Entfernungsfelder aller Ortslagen, mit Zwischenspeicher auf Platte.

    Der Aufbau kostet rund 100.000 Rasterzellen Rechenarbeit. Das faellt
    nicht ins Gewicht, solange ein Dienst dauerhaft laeuft -- aber die
    Kartenerzeugung startet einen eigenen Prozess, und dann wartet man
    bei jedem Knopfdruck erneut darauf. Deshalb wird das Ergebnis
    abgelegt und nur neu berechnet, wenn sich Zonen, Rasterweite oder
    Reichweite geaendert haben.
    """
    import base64
    z = zonen if zonen is not None else lade_zonen(P)
    z = {n: r for n, r in z.items() if r}
    schluessel = _zonen_schluessel(P, z)
    # Ablageorte in dieser Reihenfolge. Der Monitor bindet /data nur
    # lesend ein -- dort legen die Logger die Datei an, der Monitor liest
    # sie mit. Scheitert beides, dient /tmp als Rueckfall; das ueberlebt
    # immerhin die Laufzeit des Containers und damit viele Kartenaufrufe.
    name = f"_zonenfelder_{P['code'].lower()}.json"
    orte = [os.environ.get("TRACKER_ZONEN_SPEICHER"),
            os.environ.get("TRACKER_DATA_DIR") or "/data",
            tempfile.gettempdir()]
    orte = [os.path.join(o, name) for o in orte if o]

    # 1. Versuch: fertige Felder einlesen -- aus dem ersten Ort, der passt
    for datei in orte:
      try:
        with open(datei, encoding="utf-8") as f:
            abgelegt = json.load(f)
        if abgelegt.get("schluessel") == schluessel:
            felder = {}
            for n, d in abgelegt["felder"].items():
                if n not in z:
                    raise ValueError("Ortslage nicht mehr vorhanden")
                o = Zonenfeld.__new__(Zonenfeld)
                o.ringe = z[n]
                o.la0, o.lo0 = d["la0"], d["lo0"]
                o.kla, o.klo = d["kla"], d["klo"]
                o.nla, o.nlo = d["nla"], d["nlo"]
                roh = base64.b64decode(d["feld"])
                o._feld = [list(roh[i * o.nlo:(i + 1) * o.nlo])
                           for i in range(o.nla)]
                felder[n] = o
            if set(felder) == set(z):
                return felder
      except Exception:
        continue

    # 2. Neu bauen und ablegen
    felder = {n: Zonenfeld(r) for n, r in z.items()}
    try:
        inhalt = {"schluessel": schluessel, "felder": {}}
        for n, o in felder.items():
            flach = bytearray()
            for zeile in o._feld:
                flach.extend(min(w, 255) for w in zeile)
            inhalt["felder"][n] = {
                "la0": o.la0, "lo0": o.lo0, "kla": o.kla, "klo": o.klo,
                "nla": o.nla, "nlo": o.nlo,
                "feld": base64.b64encode(bytes(flach)).decode(),
            }
        roh = json.dumps(inhalt)
        for datei in orte:
            try:
                tmp = datei + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(roh)
                os.replace(tmp, datei)
                break
            except OSError:
                continue        # nicht schreibbar -- naechsten Ort versuchen
    except Exception:
        pass        # Zwischenspeicher ist Kuer, nicht Pflicht
    return felder


def _umriss_ringe(feld_obj, puffer_m=0):
    """Verschmilzt die Rasterzellen zu geschlossenen Umrisslinien.

    Statt viele Einzelrechtecke zu zeichnen, werden nur die Kanten
    zwischen bebauter und unbebauter Zelle gesammelt und zu Ringen
    verkettet. Ergebnis: eine zusammenhaengende Flaeche je Ortslage,
    Loecher inbegriffen.
    """
    f = feld_obj._feld
    nla, nlo = feld_obj.nla, feld_obj.nlo

    grenze = puffer_m / feld_obj.ZELLE_M

    def voll(i, j):
        return 0 <= i < nla and 0 <= j < nlo and f[i][j] <= grenze

    kanten = {}
    for i in range(nla):
        for j in range(nlo):
            if not voll(i, j):
                continue
            # gegen den Uhrzeigersinn, bebaute Zelle stets links
            if not voll(i - 1, j):
                kanten[(i, j)] = (i, j + 1)
            if not voll(i, j + 1):
                kanten[(i, j + 1)] = (i + 1, j + 1)
            if not voll(i + 1, j):
                kanten[(i + 1, j + 1)] = (i + 1, j)
            if not voll(i, j - 1):
                kanten[(i + 1, j)] = (i, j)

    ringe = []
    while kanten:
        start = next(iter(kanten))
        ring, p = [], start
        while p in kanten:
            ring.append(p)
            nxt = kanten.pop(p)
            p = nxt
            if p == start:
                break
        if len(ring) >= 4:
            ringe.append(ring)

    # Geraden zusammenfassen und in Koordinaten umrechnen
    zelle = feld_obj.ZELLE_M / 1000.0
    raus = []
    for ring in ringe:
        kurz = []
        for k, pt in enumerate(ring):
            v, n = ring[k - 1], ring[(k + 1) % len(ring)]
            if (pt[0] - v[0], pt[1] - v[1]) != (n[0] - pt[0], n[1] - pt[1]):
                kurz.append(pt)
        if len(kurz) < 3:
            continue
        raus.append([(feld_obj.la0 + i * zelle / feld_obj.kla,
                      feld_obj.lo0 + j * zelle / feld_obj.klo) for i, j in kurz])
    return raus


Zonenfeld.umriss = _umriss_ringe


def datenverzeichnis_pruefen(pfad, melde=print):
    """Prueft, ob in das Datenverzeichnis geschrieben werden kann.

    Haeufigste Ursache fuer ein Nein: Das Abbild laeuft als Benutzer 1000,
    das Verzeichnis gehoert aber root -- etwa weil es frueher von einem
    Container angelegt wurde, der als root lief. Die Meldung nennt den
    Ausweg, damit niemand erst im Protokoll raten muss.
    """
    import tempfile
    try:
        os.makedirs(pfad, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=pfad, prefix="_schreibprobe_"):
            pass
        return True
    except Exception as e:
        try:
            st = os.stat(pfad)
            besitz = f"gehoert {st.st_uid}:{st.st_gid}"
        except Exception:
            besitz = "Eigentuemer unbekannt"
        melde("")
        melde("=" * 66)
        melde(f" KEIN SCHREIBRECHT auf {pfad}")
        melde(f"   {type(e).__name__}: {e}")
        melde(f"   Prozess laeuft als {os.getuid()}:{os.getgid()}, "
              f"Verzeichnis {besitz}")
        melde("")
        melde(" Abhilfe, eines von beidem:")
        melde("   a) Im Stack die Variable FS_USER auf 0:0 setzen und")
        melde("      den Stack aktualisieren.")
        melde(f"   b) Auf der NAS: chown -R {os.getuid()}:{os.getgid()} "
              f"<datenverzeichnis>")
        melde("")
        melde(" Es wird nichts aufgezeichnet, solange das nicht behoben ist.")
        melde("=" * 66)
        return False
