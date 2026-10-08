#!/usr/bin/env python3
"""Luftfahrzeugkennzeichen statt Hexcode.

Drei Quellen, in dieser Reihenfolge:

1. ADS-B liefert das Kennzeichen direkt mit (Feld `r`, z. B. D-EABC).
   Der ADS-B-Logger merkt sich jede Zuordnung in `_kennzeichen.json`,
   damit sie auch dann noch bekannt ist, wenn eine Maschine spaeter nur
   ueber OGN gesehen wird oder das Feld einmal fehlt.

2. Die OGN-Geraetedatenbank (DDB) ordnet FLARM- und OGN-Kennungen ein
   Kennzeichen samt Muster zu. Frei abrufbar, rund 37.000 Geraete.
   Wird als `_ddb.json` zwischengespeichert und woechentlich erneuert.

3. Bleibt beides erfolglos, wird der Hexcode angezeigt. Nicht jedes
   Luftfahrzeug sendet ein Kennzeichen -- das ist kein Fehler.

Enthaelt keine Halterdaten. Die DDB nennt ausschliesslich Kennzeichen und
Muster; wer ein Geraet nicht veroeffentlicht sehen will, kann dem bei OGN
widersprechen, dann fehlt es hier ebenfalls.
"""
import json, os, time, urllib.request

UA = "Flugspur/1.0 (Buergerinitiative Fluglaerm; nicht-kommerziell)"
DDB_URL = "http://ddb.glidernet.org/download/?j=1"
DDB_DATEI = "_ddb.json"
REG_DATEI = "_kennzeichen.json"
DDB_MAXALTER_S = 7 * 86400


# ---------------------------------------------------------------- DDB

def ddb_aktualisieren(data_dir, zwang=False, melde=print):
    """Laedt die OGN-Geraetedatenbank, wenn sie fehlt oder alt ist."""
    pfad = os.path.join(data_dir, DDB_DATEI)
    if not zwang and os.path.exists(pfad):
        if time.time() - os.path.getmtime(pfad) < DDB_MAXALTER_S:
            return False
    try:
        req = urllib.request.Request(DDB_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            roh = json.load(r)
        schlank = {}
        for g in roh.get("devices", []):
            kz = (g.get("registration") or "").strip()
            if not kz:
                continue
            schlank[(g.get("device_id") or "").strip().upper()] = [
                kz, (g.get("aircraft_model") or "").strip()]
        if not schlank:
            raise ValueError("DDB leer")
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(schlank, f, ensure_ascii=False)
        os.replace(tmp, pfad)
        melde(f"OGN-Geraetedatenbank aktualisiert: {len(schlank)} Kennzeichen")
        return True
    except Exception as e:
        melde(f"OGN-Geraetedatenbank nicht erreichbar ({e}) -- weiter ohne. "
              f"Kennzeichen fehlen dann nur fuer FLARM-Geraete.")
        return False


def ddb_laden(data_dir):
    """Liest die zwischengespeicherte DDB. Faellt auf /tmp zurueck,
    wenn das Datenverzeichnis nur lesend eingebunden ist."""
    for d in (data_dir, "/tmp"):
        pfad = os.path.join(d, DDB_DATEI)
        if os.path.exists(pfad):
            try:
                with open(pfad, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


# ------------------------------------------------- gelernte Zuordnung

def reg_laden(data_dir):
    pfad = os.path.join(data_dir, REG_DATEI)
    if os.path.exists(pfad):
        try:
            with open(pfad, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def reg_sichern(data_dir, tabelle):
    """Schreibt die gelernten Zuordnungen zusammen mit dem Bestand."""
    pfad = os.path.join(data_dir, REG_DATEI)
    alt = reg_laden(data_dir)
    alt.update(tabelle)
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(alt, f, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, pfad)
    return len(alt)


# ----------------------------------------------------------- Aufloesung

class Namen:
    """Loest Kennungen in Kennzeichen auf. Einmal anlegen, oft fragen."""

    def __init__(self, data_dir):
        self.ddb = ddb_laden(data_dir)
        self.reg = reg_laden(data_dir)

    def lerne(self, hexid, kz, typ=None, muster=None):
        if not hexid or not kz:
            return
        h = hexid.lower()
        vorher = self.reg.get(h)
        neu = [kz, typ or (vorher[1] if vorher and len(vorher) > 1 else None),
               muster or (vorher[2] if vorher and len(vorher) > 2 else None)]
        if neu != vorher:
            self.reg[h] = neu

    def kennzeichen(self, *, hexid=None, ogn_id=None, reg=None):
        """Liefert das Kennzeichen oder None."""
        if reg:
            return reg.strip()
        if hexid:
            e = self.reg.get(hexid.lower())
            if e:
                return e[0]
        if ogn_id:
            e = self.ddb.get(ogn_id.strip().upper())
            if e:
                return e[0]
        return None

    def muster(self, *, hexid=None, ogn_id=None, typ=None, desc=None):
        if desc:
            return desc
        if typ:
            return typ
        if hexid:
            e = self.reg.get(hexid.lower())
            if e and len(e) > 2 and e[2]:
                return e[2]
            if e and len(e) > 1 and e[1]:
                return e[1]
        if ogn_id:
            e = self.ddb.get(ogn_id.strip().upper())
            if e and e[1] and e[1].lower() != "unknown":
                return e[1]
        return None

    def anzeige(self, *, hexid=None, ogn_id=None, reg=None):
        """Was in Tabellen stehen soll: Kennzeichen, sonst Hexcode."""
        kz = self.kennzeichen(hexid=hexid, ogn_id=ogn_id, reg=reg)
        if kz:
            return kz
        return (hexid or ogn_id or "?").lower()

    @property
    def umfang(self):
        return len(self.reg), len(self.ddb)


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else (
        os.environ.get("TRACKER_DATA_DIR") or "/data")
    ddb_aktualisieren(d)
    n = Namen(d)
    a, b = n.umfang
    print(f"Datenverzeichnis: {d}")
    print(f"  gelernte Zuordnungen aus ADS-B: {a}")
    print(f"  Eintraege OGN-Geraetedatenbank : {b}")
    for probe in sys.argv[2:]:
        print(f"  {probe} -> {n.anzeige(hexid=probe, ogn_id=probe)}")
