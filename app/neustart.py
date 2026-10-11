"""Erkennt, wenn der Programmcode ausgetauscht wurde, und beendet sich.

Hintergrund: Die Container binden `/app` vom Share ein und laufen mit
`restart: unless-stopped`. Wenn ein Prozess sich sauber beendet, startet
Docker ihn neu -- und liest dabei den neuen Code. Ein Update besteht
damit nur aus `git pull`; den Rest erledigt diese Datei.

Zwei Sicherungen, damit ein fehlerhafter Stand nicht den Mitschnitt
stoppt:

1. **Uebersetzungspruefung.** Vor dem Neustart wird jede Python-Datei
   uebersetzt. Scheitert das, bleibt der Prozess mit dem alten, noch im
   Speicher liegenden Code laufen und meldet den Fehler. Ein Tippfehler
   im Repository legt die Aufzeichnung also nicht lahm.

2. **Ruhefrist.** Erst wenn sich seit der letzten Aenderung eine Weile
   nichts mehr getan hat, wird neu gestartet. Sonst erwischt man einen
   halb uebertragenen `git pull`.
"""

import os
import py_compile
import sys
import tempfile
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
RUHE_S = 20.0          # so lange muss der Stand unveraendert sein
_LETZTE_MELDUNG = [0.0]


def stand(verzeichnis=APP_DIR):
    """Kennzahl ueber alle Python-Dateien: Name, Groesse, Aenderungszeit."""
    teile = []
    try:
        for name in sorted(os.listdir(verzeichnis)):
            if not name.endswith(".py"):
                continue
            pfad = os.path.join(verzeichnis, name)
            try:
                st = os.stat(pfad)
            except OSError:
                continue
            teile.append(f"{name}:{st.st_size}:{int(st.st_mtime)}")
    except OSError:
        return ""
    return "|".join(teile)


def _uebersetzbar(melde):
    """Prueft, ob der neue Stand fehlerfrei uebersetzt."""
    ziel = tempfile.mkdtemp()
    ok = True
    for name in sorted(os.listdir(APP_DIR)):
        if not name.endswith(".py"):
            continue
        try:
            py_compile.compile(os.path.join(APP_DIR, name),
                               cfile=os.path.join(ziel, name + "c"),
                               doraise=True)
        except Exception as e:
            melde(f"[neustart] Neuer Code ist fehlerhaft, bleibe beim alten "
                  f"Stand: {name}: {e}")
            ok = False
            break
    for f in os.listdir(ziel):
        try:
            os.remove(os.path.join(ziel, f))
        except OSError:
            pass
    try:
        os.rmdir(ziel)
    except OSError:
        pass
    return ok


def noetig(start_stand, melde=print):
    """True, wenn der Code getauscht wurde und sauber uebersetzt."""
    jetzt = stand()
    if not jetzt or jetzt == start_stand:
        return False
    # Ruhefrist abwarten, damit kein halber Stand erwischt wird
    time.sleep(RUHE_S)
    if stand() != jetzt:
        return False                      # wird gerade noch geschrieben
    if not _uebersetzbar(melde):
        # nicht bei jedem Durchlauf erneut meckern
        if time.time() - _LETZTE_MELDUNG[0] > 600:
            _LETZTE_MELDUNG[0] = time.time()
        return False
    return True


def beenden_wenn_neu(start_stand, melde=print, code=0):
    """Beendet den Prozess, wenn neuer Code vorliegt.

    Docker startet den Container daraufhin neu -- siehe
    `restart: unless-stopped` in der Compose-Datei.
    """
    if noetig(start_stand, melde):
        melde("[neustart] Neuer Programmstand erkannt, beende mich. "
              "Docker startet mich gleich mit dem neuen Code neu.")
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(code)


if __name__ == "__main__":
    print("Aktueller Stand von /app:")
    s = stand()
    for t in s.split("|"):
        print("  ", t)
    print(f"\n{len(s.split('|'))} Dateien. Uebersetzbar: "
          f"{'ja' if _uebersetzbar(print) else 'NEIN'}")
