# Installation auf QNAP (QTS) mit Portainer — ohne SSH

Komplett über die Weboberfläche. Kein Kommandozeilenzugang, kein Image-Build,
kein `pip install`. Dauer: etwa 15 Minuten.

Ausgelegt auf **Dauerbetrieb**: einmal eingerichtet, läuft es durch und
überlebt NAS-Neustarts.

---

## Schritt 1 — Ordner anlegen (File Station)

Öffnen Sie **File Station** und legen Sie in der Freigabe `Container` an:

```
Container/
└── flugspur/
    ├── app/
    └── data/
```

Beide Unterordner sind nötig. `data` bleibt zunächst leer.

> **Falls die Freigabe `Container` fehlt:** Sie erscheint erst, wenn
> *Container Station* installiert ist. Da Portainer bei Ihnen bereits läuft,
> ist sie mit hoher Wahrscheinlichkeit vorhanden. Andernfalls nehmen Sie eine
> beliebige andere Freigabe und passen in Schritt 4 alle Pfade entsprechend an.

---

## Schritt 2 — Dateien hochladen

Entpacken Sie `flugspur.zip` auf Ihrem PC und laden Sie in File
Station **die fünf `.py`-Dateien** in `Container/flugspur/app/` hoch:

```
adsb_logger.py   ogn_logger.py   summary.py   visualize.py   make_demo.py
```

Die Dateien müssen **direkt** in `app/` liegen, nicht in einem weiteren
Unterordner. Ein häufiger Fehler ist `app/app/adsb_logger.py` — das führt
später zu `can't open file`.

> **Wichtig, falls Sie eine Datei zwischendurch in Windows bearbeiten:**
> Nur Editoren mit Unix-Zeilenenden verwenden (Notepad++, VS Code), nicht
> den klassischen Windows-Editor. Besser: gar nicht bearbeiten, Einstellungen
> nimmt man in Schritt 4 vor.

---

## Schritt 3 — Pfadtest (unbedingt zuerst)

Dieser Schritt kostet zwei Minuten und erspart die mit Abstand häufigste
Fehlersuche. Er prüft drei Dinge auf einmal: richtiger Pfad, Schreibrecht,
Internetzugang.

1. Portainer → **Stacks** → **Add stack**
2. Name: `flugspur-pfadtest`
3. Build method: **Web editor**
4. Inhalt von `docker-compose.pfadtest.yml` einfügen
5. **Deploy the stack**
6. Portainer → **Containers** → `flugspur-pfadtest` → **Logs**

**So sieht Erfolg aus:**

```
==============================================
 Inhalt von /app :
 -rw-r--r-- 1 ... adsb_logger.py
 -rw-r--r-- 1 ... ogn_logger.py
 -rw-r--r-- 1 ... summary.py
 -rw-r--r-- 1 ... visualize.py
 -rw-r--r-- 1 ... make_demo.py
==============================================
 Schreibtest in /data :
 Schreiben moeglich - alles gut
==============================================
 Internetzugang :
 adsb.fi erreichbar, HTTP 200
==============================================
```

| Meldung | Bedeutung | Abhilfe |
|---|---|---|
| `LEER ODER NICHT VORHANDEN` | Pfad falsch oder Dateien im falschen Ordner | Pfad in File Station prüfen: rechte Maustaste → Eigenschaften zeigt den echten Pfad |
| `KEIN SCHREIBRECHT auf /data` | Ordnerrechte | In File Station Schreibrecht für `data` setzen |
| `KEIN Internetzugang` | DNS/Firewall des NAS | QTS → Netzwerk → DNS prüfen |

Erst wenn alle drei Zeilen gut aussehen, weitermachen. Danach den Stack
`flugspur-pfadtest` in Portainer **löschen** (Stacks → auswählen → Remove).

---

## Schritt 4 — Den richtigen Stack ausrollen

1. Portainer → **Stacks** → **Add stack**
2. Name: `flugspur`
3. Build method: **Web editor**
4. Inhalt von `docker-compose.qnap.yml` einfügen
5. **Deploy the stack**

Der erste Start dauert ein bis zwei Minuten — Docker lädt einmalig das
Python-Image (~45 MB). Danach laufen drei Container.

### Was Sie hier anpassen können (optional)

Direkt im Web-Editor, vor dem Deploy:

| Zeile | Wirkung |
|---|---|
| `EDLN_INTERVAL_S: "5"` | Abfragetakt. `3` = feinere Spuren, mehr Daten |
| `EDLN_MAX_ALT_FT: "10000"` | `3000` blendet Düsseldorf-Überflüge aus |
| `EDLN_RADIUS_NM: "15"` | Erfassungsradius |

Alles lässt sich später jederzeit ändern (Schritt 7).

---

## Schritt 5 — Kontrolle

Portainer → **Containers**. Sie sollten sehen:

| Container | Status |
|---|---|
| `flugspur-adsb` | running — nach ~2 Min **healthy** |
| `flugspur-ogn` | running |
| `flugspur-summary` | running |

`flugspur-summary` tut absichtlich nichts; er hält nur die Auswertung bereit.

Klicken Sie auf `flugspur-adsb` → **Logs**. Erwartet:

```
2026-10-07 19:54:17 [adsb] Start EDLN | 51.230356,6.504494 | 15.0 NM | < 10000 ft | alle 5.0s | -> /data
```

Eine gelegentliche Zeile `Quelle adsb.fi gestoert -> wechsle` ist **normal** —
der Logger wechselt dann auf adsb.lol.

Nach wenigen Minuten erscheinen in File Station unter
`Container/flugspur/data/` die ersten Dateien:

```
adsb_2026-10-07.ndjson
ogn_2026-10-07.ndjson
_heartbeat_adsb.txt
```

**Damit ist die Erfassung produktiv.** Ab hier läuft sie von selbst weiter,
auch nach einem Neustart des NAS.

---

## Schritt 6 — Auswerten (ebenfalls ohne SSH)

Portainer → **Containers** → `flugspur-summary` → **Console** → Command `/bin/sh`
→ **Connect**. Dann eintippen:

```sh
python3 /app/summary.py        # Textreport
python3 /app/visualize.py      # grafische HTML-Seite
```

Die Ergebnisse liegen anschließend **direkt in File Station** unter
`Container/flugspur/data/`:

```
report_2026-10-07.csv
flugbewegungen_2026-10-07.html
```

Von dort einfach herunterladen und im Browser öffnen. Genau dafür ist `data`
als normaler Ordner eingebunden statt als Docker-Volume — Sie kommen ohne
Umweg an Ihre Dateien.

### Layout vorab ansehen, solange noch keine Daten da sind

In derselben Konsole:

```sh
EDLN_DATA_DIR=/data/demo python3 /app/make_demo.py
EDLN_DATA_DIR=/data/demo EDLN_OUT_DIR=/data/demo EDLN_DEMO=1 python3 /app/visualize.py
```

Ergebnis in `data/demo/`. Diese Datei trägt einen roten Balken
**„BEISPIEL MIT SIMULIERTEN DATEN"** — sie zeigt nur das Layout und belegt
nichts. Niemals ohne diesen Balken weitergeben.

---

## Schritt 7 — Später etwas ändern

Portainer → **Stacks** → `flugspur` → **Editor** → Wert ändern →
**Update the stack**. Die Container starten neu, **bereits erfasste Daten
bleiben vollständig erhalten**.

Änderungen an den `.py`-Dateien: neue Version in File Station nach `app/`
hochladen, dann Stack → **Update the stack** (Haken bei *Re-pull image* ist
dafür nicht nötig).

---

## Dauerbetrieb: zwei Dinge im Blick behalten

**Speicherplatz.** Rechnen Sie mit **40–80 MB pro Monat**, also etwa 0,5–1 GB
im Jahr. Für ein NAS unkritisch, aber nicht null.

**Monatliche Sicherung und Bericht.** Einmal im Monat in der Konsole von
`flugspur-summary`:

```sh
python3 /app/visualize.py --all      # Gesamtauswertung über alle Tage
```

Die Tagesdateien in `data/` können Sie danach in File Station in einen
Unterordner `archiv/` verschieben — der Mitschnitt läuft davon ungestört
weiter, weil immer nur in die Datei des *aktuellen* Tages geschrieben wird.

> Bei sehr langen Zeiträumen wird `--all` langsam und die HTML-Datei groß.
> Ab etwa drei Monaten lieber monatsweise auswerten, indem Sie nicht
> benötigte Tagesdateien vorübergehend ins Archiv verschieben.

---

## Wenn etwas klemmt

| Symptom | Ursache | Abhilfe |
|---|---|---|
| Container startet immer wieder neu | `can't open file '/app/adsb_logger.py'` in den Logs → Dateien liegen falsch | Schritt 2 und 3 wiederholen |
| `flugspur-adsb` dauerhaft **unhealthy** | Heartbeat fehlt, meist kein Internet | Logs ansehen, Pfadtest erneut laufen lassen |
| `data/` bleibt leer | Schreibrecht oder falscher Pfad | Pfadtest |
| OGN-Datei bleibt leer, ADS-B läuft | kein OGN-Empfänger in Reichweite | Abdeckung prüfen: http://ognrange.onglide.com/ — kein Fehler des Stacks |
| `ziele=0` nachts | normal, es fliegt nichts | abwarten |
| Report sagt „zu wenig Daten" | zu kurze Laufzeit | Betriebsrichtung und Platzrundenerkennung brauchen einige Stunden |

---

## Realistische Erwartung

- **Nach 1 Tag:** erste Karte mit echten Spuren.
- **Nach 1 Woche:** Tagesgang, Wochenend-/Werktagsunterschied, Verteilung der
  Betriebsrichtungen.
- **Nach 1 Monat:** belastbare Fallzahlen zur Spurtreue — brauchbar für
  Öffentlichkeitsarbeit und den Lärmschutzbeirat.

Erfasst werden nur Maschinen mit ADS-B, MLAT-fähigem Mode-S oder FLARM/ADS-L.
Am MGL besteht **keine Transponderpflicht**, reine Mode-A/C-Maschinen bleiben
unsichtbar. Alle Mengenangaben sind **Untergrenzen**.
