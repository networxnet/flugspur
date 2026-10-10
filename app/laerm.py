"""Abschaetzung des Maximalpegels eines Ueberflugs.

Grundlage ist die Systematik, mit der in Deutschland Fluglaerm an
Landeplaetzen begutachtet wird: die LAI-Landeplatz-Fluglaermleitlinie in
Verbindung mit DIN 45684-1. Dort werden Luftfahrzeuge nach Antriebsart und
Hoechststartmasse in Gruppen eingeteilt, und jede Gruppe hat einen eigenen
Emissionsdatensatz, bezogen auf die Entfernung 300 m.

WICHTIG -- was dieses Modul ist und was nicht:

  Es ist eine *Abschaetzung* aus Flugspur und Luftfahrzeugmuster.
  Es ist *keine Messung* und *kein Gutachten*. Nicht beruecksichtigt sind
  Triebwerksleistung, Propellerdrehzahl, Flugzustand, Wind, Temperatur,
  Bodenreflexion und Abschirmung. Die Abweichung im Einzelfall kann
  mehrere Dezibel betragen. Fuer eine rechtsfeste Aussage braucht es
  Messungen nach DIN 45643.

Wofuer es trotzdem taugt: Es macht Ereignisse vergleichbar. Ein Jet in
2 km Hoehe und eine Cessna in 300 m sind nicht dasselbe, und eine reine
Entfernungsschwelle kann das nicht trennen. Ausserdem sind die Schwellen
55 und 65 dB(A) anschlussfaehig an die Werte, mit denen Behoerden
arbeiten.
"""

import math

# ---------------------------------------------------------------------------
# Bezugspegel: A-bewerteter Maximalpegel in 300 m Entfernung, in dB(A).
#
# Herleitung: Die Landeplatz-Fluglaermleitlinie (Anlage 1) gibt fuer jede
# Luftfahrzeuggruppe Oktavpegel bei der Bezugsentfernung s0 = 300 m an.
# Diese acht Oktavwerte wurden A-bewertet (Korrekturen nach DIN EN 61672
# fuer 63 Hz bis 8 kHz) und energetisch aufsummiert. Das ergibt die hier
# eingetragenen Summenpegel. Sie sind auf halbe Dezibel gerundet; die
# Rundung ist gegenueber der Modellunsicherheit bedeutungslos.
# ---------------------------------------------------------------------------
BEZUGSPEGEL_300M = {
    "P1.0": 70.0,   # Ultraleichtflugzeuge
    "P1.1": 70.0,   # Motorsegler
    "P1.2": 71.5,   # Propeller bis 2,0 t (auch Segelflugzeugschlepp)
    "P1.3": 71.5,   # Propeller bis 2,0 t
    "P1.4": 79.5,   # Propeller 2,0 bis 5,7 t
    "P2.1": 82.0,   # Propeller ueber 5,7 t, laermzertifiziert
    "P2.2": 85.0,   # Propeller ueber 5,7 t, aelter
    "S":    87.5,   # Strahlflugzeuge
    "H":    82.0,   # Hubschrauber
}

# Zusatzpegel fuer den Horizontalflugteil in der Platzrunde, in dB.
# Quelle: Landeplatz-Fluglaermleitlinie, Anlage 2. Das Regelwerk setzt
# Platzrundenbetrieb also ausdruecklich lauter an als Streckenflug --
# genau der Betrieb, um den es bei Schulflugplaetzen geht.
PLATZRUNDE_ZUSATZ = {
    "P1.0": 6.0, "P1.1": 4.0, "P1.2": 2.0, "P1.3": 2.0, "P1.4": 2.0,
    "P2.1": 5.0, "P2.2": 5.0, "S": 3.0, "H": 0.0,
}

KLARTEXT = {
    "P1.0": "Ultraleicht",
    "P1.1": "Motorsegler",
    "P1.2": "Propeller bis 2 t",
    "P1.3": "Propeller bis 2 t",
    "P1.4": "Propeller 2 bis 5,7 t",
    "P2.1": "Propeller ueber 5,7 t",
    "P2.2": "Propeller ueber 5,7 t",
    "S":    "Strahlflugzeug",
    "H":    "Hubschrauber",
    "?":    "Muster unbekannt",
}

# Luftabsorption, grob gemittelt ueber das A-bewertete Spektrum, in dB je km.
# Bei den hier betrachteten Entfernungen bis etwa 3 km traegt sie nur wenige
# Dezibel bei, darf aber nicht ganz entfallen, weil sie sonst gerade die
# lauten Quellen in grosser Entfernung ueberschaetzt.
LUFTDAEMPFUNG_DB_PRO_KM = 3.0

# Schwellen fuer die Zaehlung.
#   55 dB(A) -- Orientierungswert der DIN 18005 Beiblatt 1 fuer allgemeine
#               Wohngebiete tags; Bezugspunkt der Landeplatz-Leitlinie.
#   65 dB(A) -- Wert der Tag-Schutzzone 1 nach FluLaermG fuer bestehende
#               zivile Flugplaetze; deutlich wahrnehmbare Stoerung.
SCHWELLEN = (55.0, 65.0)

# ---------------------------------------------------------------------------
# Zuordnung ICAO-Musterkuerzel -> Luftfahrzeuggruppe
# ---------------------------------------------------------------------------
_MUSTER = {}


def _eintragen(gruppe, kuerzel):
    for k in kuerzel.split():
        _MUSTER[k] = gruppe


_eintragen("P1.0", "WT9 FDCT CTLS EV97 P28U SLG2 ULAC A5 SIRA VL3 SHCK "
                   "BREZ PIVI ZENA MCR1 SONX KITF SAVA")
_eintragen("P1.1", "DIMO S10 SF25 HK36 TS1J AS25 ARCU SF28 G109")
_eintragen("P1.2", "C150 C152 C162 C172 C72R F172 FA72 P28A P28B P28R PA18 "
                   "PA22 PA28 PA38 DR40 DR30 DR21 DR25 DR22 DV20 DA20 DA40 "
                   "AT3 SR20 SR22 M20P M20T BE23 BE24 BE33 BE35 BE36 C177 "
                   "C182 C185 RV6 RV7 RV8 RV10 AA5 AA1 GY80 TB09 TB10 TB20 "
                   "P208 P28T SF26 ZZZZ YK52 CAP1 CP10 TOBA")
_eintragen("P1.3", "C206 C207 C210 C205 BE58 BE55 P32R PA32 PA34 PA44 C303 "
                   "C310 C337 M20R SR22T DA62")
_eintragen("P1.4", "DA42 C402 C404 C414 C421 PA31 PAY1 PAY2 BE60 BE76 C208 "
                   "PC12 TBM7 TBM8 TBM9 EPIC P180")
_eintragen("P2.1", "B350 BE20 BE30 C441 SW4 AT43 AT45 AT72 DH8A DH8B DH8C "
                   "DH8D SB20 F406 D228 D328 L410")
_eintragen("S",    "C25A C25B C25C C25M C510 C525 C550 C551 C560 C56X C650 "
                   "C680 C68A C700 C750 CL30 CL35 CL60 CL64 E50P E55P E545 "
                   "E550 PRM1 LJ31 LJ35 LJ40 LJ45 LJ60 LJ75 GLF4 GLF5 GLF6 "
                   "GL5T GL7T FA7X FA8X F2TH F900 H25B HA4T BE40 A319 A320 "
                   "A321 A20N A21N B737 B738 B739 B38M E170 E190 E195 CRJ2 "
                   "CRJ9 AT76 SU95 BCS1 BCS3")
_eintragen("H",    "R22 R44 R66 EC20 EC30 EC35 EC45 EC55 EC20 H500 H269 "
                   "A109 A119 AS50 AS55 AS65 AS32 B06 B06T B407 B412 B429 "
                   "S76 S92 H125 H130 H135 H145 H155 H160 NH90 UH60 EC75")

_SCHLUESSELWORT = [
    ("HELICOPTER", "H"), ("HUBSCHRAUBER", "H"), ("ROBINSON", "H"),
    ("EUROCOPTER", "H"), ("SIKORSKY", "H"), ("BELL ", "H"),
    ("GULFSTREAM", "S"), ("LEARJET", "S"), ("CITATION", "S"),
    ("EMBRAER", "S"), ("BOMBARDIER", "S"), ("AIRBUS", "S"), ("BOEING", "S"),
    ("KING AIR", "P2.1"), ("DASH", "P2.1"),
    ("PILATUS", "P1.4"), ("CARAVAN", "P1.4"),
    ("CESSNA", "P1.2"), ("PIPER", "P1.2"), ("ROBIN", "P1.2"),
    ("DIAMOND", "P1.2"), ("CIRRUS", "P1.2"), ("MOONEY", "P1.2"),
    ("BEECH", "P1.2"), ("AQUILA", "P1.2"), ("GLIDER", "P1.1"),
]


def gruppe(muster=None, beschreibung=None):
    """Luftfahrzeuggruppe aus ICAO-Musterkuerzel oder Klartextbeschreibung.

    Liefert '?' wenn nichts zutrifft. '?' wird in der Auswertung getrennt
    ausgewiesen und nicht stillschweigend einer Gruppe zugeschlagen --
    sonst stuende eine erfundene Zahl in der Statistik.
    """
    if muster:
        g = _MUSTER.get(str(muster).strip().upper())
        if g:
            return g
    if beschreibung:
        gross = str(beschreibung).upper()
        for wort, g in _SCHLUESSELWORT:
            if wort in gross:
                return g
    return "?"


def pegel_db(grp, schraeg_m, platzrunde=False):
    """Geschaetzter Maximalpegel L_pAmax am Boden in dB(A).

    schraeg_m ist die Schraegentfernung, also der tatsaechliche Abstand
    zwischen Luftfahrzeug und Immissionsort: Wurzel aus seitlichem Abstand
    im Quadrat plus Flughoehe ueber Grund im Quadrat.

    Gerechnet wird mit Abstandsmass (6 dB je Entfernungsverdopplung) und
    Luftabsorption, ausgehend vom Bezugspegel bei 300 m.
    """
    basis = BEZUGSPEGEL_300M.get(grp)
    if basis is None:
        basis = BEZUGSPEGEL_300M["P1.2"]      # Annahme bei unbekanntem Muster
    if platzrunde:
        basis += PLATZRUNDE_ZUSATZ.get(grp, 2.0)
    s = max(float(schraeg_m), 50.0)           # unter 50 m wird das Modell sinnlos
    return (basis
            - 20.0 * math.log10(s / 300.0)
            - LUFTDAEMPFUNG_DB_PRO_KM * max(0.0, (s - 300.0) / 1000.0))


def entfernung_fuer_pegel(grp, db, platzrunde=False):
    """Umkehrung: Bei welcher Schraegentfernung wird der Pegel erreicht?

    Nur fuer Dokumentation und Plausibilitaetspruefung gedacht.

    Geloest wird durch Intervallhalbierung, nicht durch Umstellen der
    Formel: Wegen der Luftabsorption ist der Pegelverlauf nicht
    logarithmisch, eine naive Iteration laeuft dort auseinander.
    """
    lo, hi = 10.0, 100000.0
    if pegel_db(grp, lo, platzrunde) < db:
        return lo
    if pegel_db(grp, hi, platzrunde) > db:
        return hi
    for _ in range(200):
        mitte = (lo + hi) / 2.0
        if pegel_db(grp, mitte, platzrunde) > db:
            lo = mitte
        else:
            hi = mitte
    return (lo + hi) / 2.0


def tabelle():
    """Pegel-Entfernungs-Tabelle fuer die Dokumentation."""
    zeilen = []
    for g in ("P1.0", "P1.2", "P1.4", "P2.1", "H", "S"):
        zeilen.append((g, KLARTEXT[g], BEZUGSPEGEL_300M[g],
                       entfernung_fuer_pegel(g, 65.0),
                       entfernung_fuer_pegel(g, 55.0)))
    return zeilen


if __name__ == "__main__":
    print("Bezugspegel in 300 m und Entfernungen, bei denen die Schwellen")
    print("unterschritten werden (ohne Platzrundenzuschlag):\n")
    print(f"  {'Gruppe':7s} {'Beschreibung':24s} {'300 m':>8s} "
          f"{'65 dB(A)':>10s} {'55 dB(A)':>10s}")
    for g, text, basis, d65, d55 in tabelle():
        print(f"  {g:7s} {text:24s} {basis:6.1f} dB {d65:8.0f} m {d55:8.0f} m")
    print("\nAlle Werte sind Abschaetzungen, keine Messungen.")
