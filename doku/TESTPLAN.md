# Aufsetzen und testen — der Plan für die ersten zwei Wochen

Ziel dieser Phase: belegen, dass die Erfassung zuverlässig läuft und die
Zahlen stimmen. **Erst danach** Image bauen, erst danach weitergeben.

Variante für die Testphase: **`docker-compose.qnap.yml`** (eingehängter
Ordner). Nicht weil es schneller eingerichtet ist, sondern weil ein Fehler
sich in einer Minute beheben lässt — Datei ersetzen, Container neu starten.
Beim fertigen Image wären es fünf bis zehn Minuten je Versuch.

---

## Heute (etwa 30 Minuten)

| # | Schritt | Anleitung |
|---|---|---|
| 1 | Ordner `Container/flugspur/app` und `.../data` anlegen, fünf `.py`-Dateien und `plaetze/` hochladen | `INSTALLATION_QNAP.md` Schritt 1–2 |
| 2 | Pfadtest-Stack ausrollen, Logs prüfen, Stack wieder löschen | Schritt 3 |
| 3 | Stack `flugspur` ausrollen | Schritt 4 |
| 4 | **Selbsttest laufen lassen** | siehe unten |

### Der Selbsttest

Portainer → **Containers** → `flugspur-summary` → **Console** → `/bin/sh` →
**Connect**:

```sh
python3 /app/selbsttest.py
```

Dauert rund 70 Sekunden und prüft in einem Durchgang: Profil, Schreibrechte,
beide ADS-B-Quellen, OGN-Netz, einen echten 40-Sekunden-Mitschnitt, die
Auswertung und die Grafik. Am Ende steht **BESTANDEN** oder
**FEHLGESCHLAGEN** mit Begründung.

So sieht ein guter Lauf aus:

```
[ OK ] Profil geladen: EDLN -- Moenchengladbach
[ OK ] 8 Ortslagen, alle plausibel (2.2-5.4 km)
[ OK ] Schreiben in /data moeglich
[ OK ] adsb.fi erreichbar
[ OK ] OGN-Netz liefert Daten
[ OK ] Mitschnitt funktioniert
[ OK ] Auswertung laeuft durch
[ OK ] Grafische Auswertung erzeugt
 BESTANDEN -- alle Pruefungen fehlerfrei
```

**Hinweise sind kein Fehler.** „0 Positionen erfasst" ist nachts normal,
„OGN verbunden, aber keine Positionen" heißt, dass gerade nichts
Segelflugartiges unterwegs ist. Entscheidend sind die Zeilen mit `[FEHL]`.

Schicken Sie mir die Ausgabe — dann sehe ich mit einem Blick, ob alles sitzt.

---

## Tag 2: stimmen die Zahlen?

Das ist der eigentliche Test. Dass Software läuft, heißt nicht, dass sie
Richtiges misst.

**Gegenprobe am Fenster.** Suchen Sie sich eine halbe Stunde mit sichtbarem
Flugbetrieb und notieren Sie grob, was Sie hören und sehen. Danach:

```sh
python3 /app/summary.py
```

Zu vergleichen ist nicht die exakte Zahl, sondern die Größenordnung. Wenn Sie
zwölf Überflüge zählen und das Werkzeug meldet zwei, stimmt etwas nicht — oder
es waren Maschinen ohne Transponder, was selbst ein Befund wäre.

**Gegenprobe gegen eine zweite Quelle.** Öffnen Sie während des Mitschnitts
`globe.adsbexchange.com` oder `flightradar24.com` und schauen Sie, ob
dieselben Maschinen auftauchen. Abweichungen nach unten sind zu erwarten
(MLAT-Abdeckung), Abweichungen nach oben wären ein Fehler.

**Plausibilität der Ortszuordnung.** Im Report:

```
Willich-Schiefbahn/Unterbruch       14   min  920 ft ...
```

Fragen Sie jemanden vor Ort, ob das zum Empfinden passt. Eine Ortslage, die
immer null zeigt, obwohl dort geklagt wird, deutet auf falsche Koordinaten
im Profil hin.

---

## Tag 3–7: läuft es durch?

Einmal täglich, zehn Sekunden:

```sh
cat /data/_heartbeat_adsb.txt
```

Der Zeitstempel darf nicht älter als eine Minute sein. In Portainer genügt
der Blick, ob `flugspur-adsb` **healthy** ist.

**Worauf zu achten ist:**

| Beobachtung | Bedeutung |
|---|---|
| Container hat neu gestartet | in den Logs nach dem Grund sehen |
| Tagesdatei fehlt | Mitternachtswechsel hat nicht funktioniert — melden |
| OGN-Datei bleibt dauerhaft leer | kein OGN-Empfänger in Reichweite oder Port 14580 blockiert |
| Datei wächst auffällig schnell | Höhenfilter zu weit, `TRACKER_MAX_ALT_FT` senken |

Nach dem ersten Wochenende lohnt sich:

```sh
python3 /app/visualize.py --all
```

Dann sehen Sie Werktag gegen Wochenende — der erste Befund, der
öffentlichkeitstauglich ist.

---

## Nach zwei Wochen: Bilanz

Prüfen Sie diese fünf Punkte, bevor wir weitergehen:

1. **Lückenlosigkeit** — für jeden Tag eine Datei, keine Ausfälle über Stunden?
2. **Plausibilität** — passen Tagesgang und Betriebsrichtung zum Empfinden
   vor Ort?
3. **Musterspektrum** — tauchen die bekannten Schulflugzeuge auf?
4. **Ortszuordnung** — sind die betroffenen Orte die erwarteten?
5. **Speicherbedarf** — hochgerechnet aufs Jahr noch vertretbar?

Sind alle fünf in Ordnung, machen wir drei Dinge:

- **Image bauen** (`INSTALLATION_IMAGE.md`) und auf eine feste Version
  festlegen — ab dann ist nachweisbar, welche Programmfassung welche Zahlen
  erzeugt hat. Für Veröffentlichungen ist das wichtig.
- **Profil nachschärfen** — Ortslagen ergänzen, Schwellenwerte justieren,
  die offene Annahme zur Zuordnung Platzrunde Nord/Süd ↔ Betriebsrichtung
  überprüfen.
- **Erst dann weitergeben.** Ein Werkzeug, das bei anderen Initiativen
  Fehler produziert, schadet der Sache mehr, als es nützt.

---

## Wenn etwas klemmt

Schicken Sie mir drei Dinge, dann kann ich gezielt helfen statt zu raten:

1. die vollständige Ausgabe von `python3 /app/selbsttest.py`
2. die letzten Zeilen aus `docker logs flugspur-adsb`
3. die Ausgabe von `ls -la /data`

---

## Was in dieser Phase ausdrücklich **nicht** passiert

- **Keine Veröffentlichung von Zahlen.** Zwei Wochen sind keine belastbare
  Grundlage, und unverifizierte Zahlen in der Presse sind nur einmal
  korrigierbar.
- **Keine Weitergabe an andere Initiativen.** Erst wenn es bei Ihnen stabil
  läuft.
- **Kein Ausbau der Hardware.** Ob sich ein eigener Empfänger lohnt, zeigt
  sich erst, wenn wir wissen, wie groß die Lücke durch fehlende Transponder
  tatsächlich ist.
