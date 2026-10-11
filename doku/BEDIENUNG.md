# Bedienung des Mitschnitt-Stacks — Schritt für Schritt

Diese Anleitung beschreibt den Alltag: starten, kontrollieren, auswerten,
Daten herausholen, nachjustieren, beenden. Die reine Installation steht in
`README.md`.

---

## 0. Was läuft da eigentlich?

Drei Container teilen sich **ein** Datenverzeichnis (`/data`, Docker-Volume
`edln_data`):

```
  flugspur-adsb  ──┐
               ├──►  /data  ──►  flugspur-summary  ──►  Report + CSV
  flugspur-ogn   ──┘
```

| Container | Rolle | Verhalten |
|---|---|---|
| `flugspur-adsb` | fragt alle 5 s die ADS-B-Netze ab | schreibt dauerhaft, Neustart automatisch |
| `flugspur-ogn` | hält eine Dauerverbindung zum OGN-APRS-Netz | schreibt dauerhaft, reconnect nach 30 s |
| `flugspur-summary` | tut im Leerlauf nichts | wird nur auf Zuruf benutzt |

Dass `flugspur-summary` „nichts tut“, ist Absicht: Er hält nur die Auswertelogik
und den Zugriff aufs Volume bereit, damit Sie jederzeit ohne Installation
einen Report ziehen können.

---

## 1. Dateien im Datenverzeichnis

```
/data/
├── adsb_2026-09-27.ndjson     ein Tag ADS-B/MLAT, eine Zeile = eine Position
├── ogn_2026-09-27.ndjson      ein Tag FLARM/ADS-L
├── _heartbeat_adsb.txt        Lebenszeichen
├── _heartbeat_ogn.txt         Lebenszeichen
└── report_2026-09-27.csv      entsteht beim Auswerten
```

Pro Tag entstehen neue Dateien; um Mitternacht wird automatisch umgeschaltet.
Nichts wird überschrieben — bereits geschriebene Tage bleiben unangetastet.

---

## 1. Kartenhintergrund und Ortszonen

Die Karte zeigt eine OpenStreetMap-Grundlage, **Nordpfeil oben rechts**
und einen **Maßstabsbalken unten links**. Die Ortslagen sind keine Kreise
mehr, sondern die tatsächlich bebauten Flächen laut OpenStreetMap.

Jede Ortslage hat eine eigene Farbe; die vielen OSM-Teilflächen werden
über ein 100-m-Raster zu **einer** Fläche je Ort verschmolzen.

### Wann ein Lärmereignis zählt

Nicht beim direkten Überflug, sondern nach **Schrägentfernung** zur
bebauten Fläche — Standard 1.500 m, einstellbar über `laerm_schraeg_m`.

Der Grund: Für die Belastung zählt der Abstand zum Ohr, und der setzt
sich aus seitlichem Abstand und Flughöhe zusammen.

| Fall | Schrägentfernung | zählt |
|---|---|---|
| Cessna, 900 ft, 600 m seitlich | 752 m | ja |
| Airbus, 7.000 ft, direkt darüber | 2.136 m | nein |

Ein reiner „über der Fläche"-Test würde genau das Gegenteil liefern —
den hohen Verkehrsjet zählen und das tief fliegende Schulflugzeug
nebenan übersehen. Die Tabelle weist zusätzlich **tief** (höchstens
2.500 ft) getrennt von **gesamt** aus.

Beides wird einmalig geholt und liegt danach im Profil:

```sh
python3 /app/zonen_holen.py       Ortsumrisse aus OpenStreetMap
python3 /app/grundkarte.py        Kartenkacheln einbetten
```

Danach arbeitet alles offline weiter. Die Auswertung wächst dadurch von
etwa 15 kB auf rund 0,7 MB je Datei — der Preis dafür, dass sie auch in
fünf Jahren noch dieselbe Karte zeigt, ohne Internet.

**Für einen neuen Flugplatz** beide Befehle einmal ausführen, siehe
`doku/NEUER_FLUGPLATZ.md`.

Kartengrundlage und Ortsumrisse: © OpenStreetMap-Mitwirkende, Lizenz ODbL.

---

## 2. Luftfahrzeugkennzeichen statt Hexcode

Angezeigt wird das Kennzeichen (`D-EOQL`), darunter klein der technische
Hexcode (`3d2b4b`). Der Hexcode bleibt sichtbar, weil er die eindeutige
Kennung ist — Kennzeichen können bei Halterwechsel neu vergeben werden.

Woher das Kennzeichen kommt:

1. **ADS-B liefert es mit.** In einer Stichprobe hatten 42 von 42 Zielen
   ein Kennzeichen. Der Logger merkt sich jede Zuordnung in
   `_kennzeichen.json`, damit sie auch später bekannt bleibt.
2. **Die OGN-Gerätedatenbank** ordnet FLARM-Kennungen ein Kennzeichen und
   Muster zu, rund 34.000 Einträge. Liegt als `_ddb.json` im
   Datenverzeichnis und wird wöchentlich erneuert.
3. **Sonst der Hexcode.** Nicht jedes Luftfahrzeug sendet ein
   Kennzeichen. Das ist kein Fehler, sondern die Realität der Rohdaten.

Prüfen, wie viele Zuordnungen bekannt sind:

```sh
docker exec -it flugspur-summary python3 /app/kennzeichen.py /data
```

**Datenschutz:** Erfasst werden Kennzeichen und Muster, keine Halter- oder
Personendaten. Die OGN-Datenbank enthält nur, was Geräteinhaber selbst
veröffentlichen; wer widerspricht, erscheint dort nicht. Für eine
Lärmauswertung ist ohnehin das Muster relevant, nicht der Halter.

---

## 1a. Live-Monitor im Browser

```
http://<Adresse-Ihres-NAS>:8099
```

Zeigt, was gerade hereinkommt, und aktualisiert sich alle 10 Sekunden
selbst — zum Offenlassen auf einem zweiten Bildschirm:

- **Ampel** für ADS-B und OGN (grün unter 90 s, gelb bis 5 Min, rot darüber)
- gerade in der Luft, davon tief fliegend
- Meldungen der letzten 5 Minuten, Maschinen der letzten Stunde und heute
- Tabelle der aktuell sichtbaren Maschinen mit Muster, Höhe, Tempo,
  Entfernung und Quelle — tief fliegende sind rot hinterlegt
- Überflüge je Ortslage seit Mitternacht
- Dateigrößen und Gesamtverbrauch

**Auswertung auf Knopfdruck.** Oben auf der Seite stehen Schaltflächen:

| Knopf | Ergebnis |
|---|---|
| Karte heute / gestern | grafische Auswertung des Tages |
| Karte alle N Tage | alles zusammengefasst |
| Text heute / gestern | Textauswertung wie `summary.py` |

Die Auswertung wird beim Anklicken frisch berechnet, nichts ist
zwischengespeichert. Je nach Datenmenge dauert das einige Sekunden.

Das Ergebnis landet in einem Arbeitsverzeichnis **innerhalb** des
Containers, nicht in `/data` — der Monitor hat dort bewusst kein
Schreibrecht. Zum Archivieren weiterhin `visualize.py` im
Summary-Container aufrufen, das schreibt nach `/data`.

Maschinenlesbar für eigene Auswertungen: `http://<NAS>:8099/json`
Kurzprüfung, ob der Server lebt: `http://<NAS>:8099/healthz` → `ok`

Zeigt die Seite nichts: **`doku/MONITOR_GEHT_NICHT.md`** geht die
Ursachen der Reihe nach durch.

Ohne Browser geht es auch im Terminal:

```sh
docker exec -it flugspur-monitor python3 /app/monitor.py --konsole
```

Der Monitor hängt das Datenverzeichnis **nur lesend** ein — er kann den
Mitschnitt nicht beschädigen.

---

## 1b. Selbsttest — prüft alles auf einmal

```sh
docker exec flugspur-summary python3 /app/selbsttest.py
```

70 Sekunden. Prüft Profil, Schreibrechte, beide ADS-B-Quellen, das OGN-Netz,
einen echten 40-Sekunden-Mitschnitt, die Auswertung und die Grafik. Nach
jeder Änderung an Profil oder Konfiguration sinnvoll.

Zeilen mit `[hinw]` sind kein Fehler — „0 Positionen" ist nachts normal.
Entscheidend sind `[FEHL]`-Zeilen.

---

## 2. Läuft es? (die einzige Routinekontrolle)

```bash
docker exec flugspur-adsb cat /data/_heartbeat_adsb.txt
```

```
1790509705
2026-09-27 11:48:25      <- darf nicht älter als ~1 Minute sein
ziele=11                 <- gerade sichtbare Luftfahrzeuge
gesamt=286               <- Positionen seit Containerstart
quelle=adsb.fi           <- aktuell genutztes Netz
```

Dasselbe für OGN:

```bash
docker exec flugspur-ogn cat /data/_heartbeat_ogn.txt
```

**In Portainer genügt ein Blick:** `flugspur-adsb` muss grün/**healthy** sein. Der
Healthcheck prüft genau diesen Zeitstempel und schlägt an, wenn er 3 Minuten
ausbleibt.

Laufendes Protokoll mitlesen:

```bash
docker logs -f flugspur-adsb
docker logs -f flugspur-ogn
```

Normal sieht das so aus:

```
2026-09-27 11:54:17 [adsb] Start EDLN | 51.230356,6.504494 | 15.0 NM | < 10000 ft | alle 3.0s | -> /data
2026-09-27 11:54:28 [ogn]  100 OGN-Positionen erfasst
```

Eine gelegentliche Zeile `Quelle adsb.fi gestoert -> wechsle` ist **kein
Problem** — der Logger springt dann auf adsb.lol und kommt später zurück.

---

## 3. Auswerten

Immer über den `summary`-Container:

```bash
# letzter vorhandener Tag
docker exec flugspur-summary python3 /app/summary.py

# bestimmter Tag
docker exec flugspur-summary python3 /app/summary.py 2026-09-28

# alle Tage nacheinander
docker exec flugspur-summary python3 /app/summary.py --all
```

### Wie der Report zu lesen ist

**Musterspektrum** — wie viele *verschiedene* Luftfahrzeuge je Typ erfasst
wurden, nicht wie viele Bewegungen.

```
   22  unbekannt
    3  PIPER PA-28-140/150/160/180
    1  ROTORSPORT MTOSport
    1  GUIMBAL G-2 Cabri
```

`unbekannt` sind fast immer OGN-Ziele: FLARM überträgt keinen Klartext-Typ.
Das ist normal und kein Fehler. Die Schulflugflotte (PA-28, C172, Remos) und
lärmauffällige Muster (Tragschrauber MTOSport, Hubschrauber Cabri) erscheinen
dagegen namentlich — genau die Maschinen, um die es in der Debatte geht.

**Platzrundenverdacht** — Maschinen, die ≥ 8 Minuten tief (≤ 2500 ft) im
Nahbereich kreisen. Das ist der Schulflug-/Platzrundenbetrieb:

```
  3c6def  PIPER PA-28              47 min   612 Pos  min 1050 ft
```

**Betriebsrichtung** — geschätzt aus dem Kurs tief fliegender Ziele nahe der
Pistenachse. Sagt Ihnen, welche Seite an dem Tag belastet war.

**Überflugereignisse je Ortslage** — der politisch entscheidende Block:

```
  Willich-Schiefbahn/Unterbruch       14   min  920 ft   median 1180 ft   unter 1500 ft: 11
```

Ein „Ereignis“ = ein Luftfahrzeug passiert den Ort im 1-km-Radius; erneutes
Zählen erst nach 3 Minuten, damit eine kreisende Maschine nicht als Dauerlärm
mehrfach pro Runde zählt — **jede Platzrunde zählt also als ein Überflug**.

Zusätzlich landet alles maschinenlesbar in `/data/report_TAG.csv`.

> **Wichtig zur Beweisführung:** Überflüge über Schiefbahn/Unterbruch sind
> nicht per se rechtswidrig. Die Vereinbarung, den Unterbruch nicht zu
> überfliegen, ist **nicht rechtsverbindlich**, und eine verbindliche
> Mindestflughöhe existiert dort ebenfalls nicht. Der Wert dieser Zahlen
> liegt darin, das *tatsächliche Ausmaß* zu belegen — nicht darin, einen
> Rechtsverstoß nachzuweisen.

---

## 3b. Visuelle Aufbereitung für Politik und Öffentlichkeit

Der Textreport ist für Sie. Für Ratsmitglieder, Presse und Bürgerversammlungen
gibt es eine Bildversion:

```bash
docker exec flugspur-summary python3 /app/visualize.py              # letzter Tag
docker exec flugspur-summary python3 /app/visualize.py 2026-10-07   # bestimmter Tag
docker exec flugspur-summary python3 /app/visualize.py --all        # alles zusammen
docker cp flugspur-summary:/data/flugbewegungen_2026-10-07.html .
```

Heraus kommt **eine einzige HTML-Datei**. Alles ist eingebettet — keine
Kartendienste, keine Internetverbindung, keine Zusatzsoftware. Sie können sie
per Mail verschicken, offline auf dem Beamer öffnen und als PDF ausdrucken
(im Browser: Drucken → Als PDF sichern).

Die Seite enthält fünf Blöcke, bewusst in dieser Reihenfolge:

1. **Vier Kennzahlen** ganz oben — Luftfahrzeuge, Positionen, Ortsüberflüge,
   davon unter 1500 ft. Das ist die Zusammenfassung für alle, die nur zehn
   Sekunden Zeit haben.
2. **Karte mit den tatsächlichen Flugspuren.** Jede Linie ein Flug, die Farbe
   zeigt die Höhe: **rot = tief = laut**, blau = hoher Durchgangsverkehr.
   Ortslagen sind beschriftet und mit ihrem 1-km-Radius eingezeichnet.
   Das ist das Bild, das ohne Erklärung wirkt.
3. **Dichtekarte** (nur Flüge unter 2500 ft): Je dunkler ein 500-m-Feld, desto
   öfter überflogen. Hier sieht man sofort, ob der Verkehr der empfohlenen
   Platzrunde folgt oder systematisch nach außen driftet.
4. **Balken je Ortslage**, sortiert nach Betroffenheit, mit niedrigster
   gemessener Höhe.
5. **Tagesgang und Musterspektrum** — wann geflogen wird und womit.

Jede Grafik hat einen erklärenden Satz darüber. Am Ende steht ein
Einschränkungskasten, der die Untergrenzen-Problematik und die fehlende
Rechtsverbindlichkeit offenlegt. **Lassen Sie den drin** — er nimmt der
Gegenseite das wirksamste Gegenargument vorweg.

### Erst das Layout ansehen, bevor Daten da sind

```bash
docker exec flugspur-summary sh -c \
  "EDLN_DATA_DIR=/tmp/demo python3 /app/make_demo.py && \
   EDLN_DATA_DIR=/tmp/demo EDLN_OUT_DIR=/tmp/demo EDLN_DEMO=1 python3 /app/visualize.py"
docker cp flugspur-summary:/tmp/demo/flugbewegungen_$(date +%F).html beispiel.html
```

`make_demo.py` erzeugt einen **erfundenen** Tag mit typischem
Platzrundenbetrieb. Die Ausgabe trägt dann einen roten Warnbalken
„BEISPIEL MIT SIMULIERTEN DATEN“. Damit können Sie Layout und Argumentation
vorab abstimmen, ohne auf echte Daten zu warten — und ohne je Gefahr zu
laufen, Erfundenes als Beleg zu präsentieren. Verwenden Sie Demo-Dateien
niemals ohne diesen Balken.

### Kartenausschnitt anpassen

Standard sind 11 km um den Flughafen — das zeigt die Platzrunde formatfüllend.
Für einen Überblick inklusive Düsseldorfer Anflugverkehr:

```bash
docker exec -e EDLN_VIEW_KM=25 flugspur-summary python3 /app/visualize.py
```

---

## 4. Ein einzelnes Flugzeug nachverfolgen

```bash
docker exec flugspur-summary sh -c \
  "grep '3c6def' /data/adsb_2026-09-27.ndjson | head -20"
```

Jede Zeile ist ein vollständiger Datensatz mit Zeit, Position, Höhe,
Geschwindigkeit, Kurs, Steig-/Sinkrate und Kennung.

---

## 5. Daten herausholen

Gesamtes Volume als Archiv ins aktuelle Verzeichnis:

```bash
docker run --rm -v flugspur_data:/d -v "$(pwd)":/out alpine \
  tar czf /out/edln_daten.tar.gz -C /d .
```

Nur die CSV-Reports:

```bash
docker cp flugspur-summary:/data/report_2026-09-27.csv .
```

Den exakten Volume-Namen zeigt `docker volume ls` (Portainer stellt dem
Stacknamen ein Präfix voran, daher `flugspur_data`).

**Das Archiv können Sie mir hochladen** — daraus baue ich Spurtreue-Analyse,
Höhenprofile über Unterbruch, Musterspektrum und die Betroffenheitskarte
für alle Anrainerkommunen.

---

## 6. Nachjustieren

Werte in `docker-compose.yml` ändern, dann in Portainer **Update the stack**
(oder `docker compose up -d`). Bereits erfasste Daten bleiben erhalten.

| Sie wollen … | Stellschraube |
|---|---|
| feinere Spuren (engere Kurven sichtbar) | `EDLN_INTERVAL_S: "3"` oder `"2"` |
| weniger Datenmenge | `EDLN_INTERVAL_S: "10"` |
| nur Platzrundenverkehr, keine Airliner | `EDLN_MAX_ALT_FT: "3000"` |
| größeres Gebiet | `EDLN_RADIUS_NM: "20"` |
| strengere Überflugdefinition | `EDLN_OVERFLIGHT_KM: "0.5"` |
| weitere Ortslagen bewerten | Liste `ORTE` in `app/summary.py` ergänzen, dann Stack neu bauen |

Ein Intervall unter 2 Sekunden bringt nichts: Die Netze aktualisieren selbst
nicht schneller, und übermäßige Abfragen riskieren eine Sperre.

---

## 7. Beenden und aufräumen

```bash
docker compose stop        # pausieren, Daten bleiben
docker compose down        # Container entfernen, Volume bleibt
docker compose down -v     # ACHTUNG: löscht auch alle Mitschnitte
```

In Portainer: Stack → *Stop* bzw. *Remove*. „Remove“ löscht das Volume
standardmäßig **nicht** — die Daten überleben.

---

## 8. Wenn etwas nicht stimmt

| Symptom | Ursache / Abhilfe |
|---|---|
| Heartbeat veraltet, Container läuft | NAS ohne Internet oder DNS-Problem. `docker exec flugspur-adsb python3 -c "import urllib.request;print(urllib.request.urlopen('https://opendata.adsb.fi',timeout=10).status)"` |
| `ziele=0` über Stunden bei Tag | Radius/Höhenfilter zu eng, oder es fliegt wirklich nichts (Nacht, Wetter). Zum Test `EDLN_MAX_ALT_FT: "45000"` — dann müssen Düsseldorf-Anflüge erscheinen. |
| OGN schreibt nichts | Kein OGN-Empfänger in Reichweite. Abdeckung prüfen: http://ognrange.onglide.com/ |
| Build scheitert mit `COPY app/` | Der Ordner `app/` mit den drei `.py`-Dateien liegt nicht neben dem `Dockerfile`. |
| Report sagt „zu wenig Daten“ | Normal bei kurzer Laufzeit. Betriebsrichtung und Platzrundenverdacht brauchen einige Stunden. |
| Container startet immer neu | `docker logs flugspur-adsb` zeigt den Grund; meist ein Tippfehler in einer Umgebungsvariable. |

---

## 9. Realistische Erwartung

- **Nach 1 Stunde:** erste Muster und Überflüge sichtbar — ein Gefühl, mehr nicht.
- **Nach 1 Woche:** belastbare Tagesgänge, Wochenend-/Werktagsunterschied,
  Verteilung der Betriebsrichtungen.
- **Nach 1 Monat:** Aussagen zur Spurtreue mit ausreichender Fallzahl; brauchbar
  für Öffentlichkeitsarbeit und Gespräche mit dem Lärmschutzbeirat.

Erfasst werden nur Maschinen mit **ADS-B, MLAT-fähigem Mode-S oder FLARM/ADS-L**.
Am MGL besteht **keine Transponderpflicht**, reine Mode-A/C-Maschinen bleiben
unsichtbar. Alle Mengenangaben sind daher **Untergrenzen** — für Aussagen zur
Spurtreue der erfassten Flüge ist das unerheblich, für absolute
Bewegungszahlen nicht.

## Ortslagen: Abgrenzung und Herkunft

Die Zonen stammen aus OpenStreetMap (`zonen_holen.py`). Zwei Ortslagen sind
abweichend festgelegt, weil OSM sie nicht sachgerecht abbildet:

* **Schiefbahn-Unterbruch** – OSM kennt hier nur einen Punkt und wenige
  Gebaeudeflaechen (zusammen rund 3 ha). Das tatsaechliche Gebiet Unterbruch
  reicht von der Ostkante Schiefbahns bis an die A 52 im Sueden und wurde
  von der Buergerinitiative in der Karte abgegrenzt; die Grenze liegt als
  14-Eck mit 2,11 km2 in `zonen_edln.json` unter `grenze`. Die urspruenglich
  aus OSM bezogenen bebauten Teilflaechen bleiben unter
  `teilflaechen_bebaut` erhalten.
  Die Umrechnung der Kartenmarkierung in Koordinaten erfolgte ueber drei
  Passpunkte (Fernmeldeturm, Modellflugplatz, Kaiserhof); die Restabweichung
  liegt bei etwa 50 m. Fuer eine Gebietsgrenze ist das ausreichend, fuer
  Aussagen ueber einzelne Grundstuecke nicht.
* **Kaarst-Vorst** – endet an Holzbuettgen. Holzbuettgen ist seither eine
  eigene Ortslage (`Kaarst-Holzbuettgen`), damit Vorst nicht faelschlich
  dessen Flugbewegungen zugerechnet bekommt.

Soll eine Grenze geaendert werden, genuegt es, die Punktliste in
`zonen_edln.json` zu ersetzen. Die Entfernungsfelder werden bei jedem Lauf
neu aufgebaut, ein erneutes `zonen_holen.py` ist nicht noetig.


## Wann lohnt sich die Zählung vor Ort?

    python3 /app/beste_zeit.py --fenster 60

Wertet alle bisher aufgezeichneten Tage aus und nennt das Zeitfenster mit
den meisten Flugbewegungen, aufgeschlüsselt nach Wochentag und Stunde.
Damit laesst sich der Vergleich von Hand gezaehlter und automatisch
erfasster Bewegungen auf die Zeit legen, in der er am meisten hergibt.

Mit `--tief` werden nur Bewegungen bis zur eingestellten Grenze
(`low_ft`, derzeit 2500 ft) gezaehlt — das trifft den Platzrundenbetrieb
besser und blendet hohen Durchgangsverkehr Richtung Duesseldorf aus.


## Gerade Linien quer ueber die Karte

Dafuer gibt es drei Ursachen, die gleich aussehen: ein echter
Geradeausflug, eine Empfangsluecke (die Karte verbindet zwei Meldungen,
zwischen denen Positionen fehlen) oder eine Verwechslung, wenn zwei
Maschinen dieselbe Kennung tragen.

Unterscheiden laesst sich das ueber die Geschwindigkeit, die ein
Streckenstueck voraussetzt:

    python3 /app/spuren_pruefen.py --tag 2026-10-10

Die Karte trennt Spuren inzwischen nicht nur bei Pausen ueber 120 s,
sondern auch dann, wenn ein Streckenstueck mehr als 800 km/h voraussetzen
wuerde. Was danach noch als lange Gerade sichtbar bleibt, ist kein Fehler.


## Updates

Es gibt nichts zu tun. Der Dienst `aktualisierer` holt alle 15 Minuten
den neuen Stand aus dem Repository, die Dauerprozesse starten sich selbst
neu. Einzelheiten und das Abschalten: `GIT_ARBEITSKOPIE.md`.

Nachsehen, ob es geklappt hat:

    docker logs --tail 20 flugspur-aktualisierer
    docker logs --tail 20 flugspur-monitor

Im Monitor-Protokoll steht bei einem Wechsel die Zeile
`[neustart] Neuer Programmstand erkannt, beende mich.`
