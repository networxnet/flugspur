# Einen weiteren Flugplatz einrichten

Alles Ortsspezifische steckt in einer JSON-Datei unter `app/plaetze/`.
Im Code steht nichts mehr über Mönchengladbach.

```
app/plaetze/
├── edln.json     Mönchengladbach
└── eddl.json     Düsseldorf (siehe Warnung unten)
```

Auswahl über eine einzige Umgebungsvariable:

```yaml
environment:
  TRACKER_PLATZ: "edln"
```

---

## Vorher prüfen: lohnt sich ein eigener Mitschnitt überhaupt?

Diese Frage ist wichtiger als die Technik. Ein Eigenbau ist dort sinnvoll,
wo **keine amtlichen Daten** verfügbar sind — typischerweise an kleinen
Plätzen. An großen Verkehrsflughäfen gibt es meist Besseres.

| Prüfen Sie | wenn vorhanden |
|---|---|
| Lärmportal des Flughafens (z. B. TraVis in Düsseldorf) | kalibrierte Lärmpegel, Flugplandaten, Historie — besser als Eigenbau |
| DFS STANLY_Track | 14 Tage Radarspuren in amtlicher Qualität |
| Deutscher Fluglärmdienst (dfld.de) | lange Historie, teils mit Messstellen |
| Lärmmessstellen der Kommune | belastbare Pegel statt bloßer Überflugzahlen |

**Bei Mönchengladbach gibt es nichts davon** — kein Portal, keine
Messstellen, keine Transponderpflicht. Deshalb der Eigenbau.

**Bei Düsseldorf gibt es alles davon.** Das mitgelieferte `eddl.json` ist
deshalb ausdrücklich **kein Ersatz** für TraVis, sondern für Quervergleiche
und Plausibilitätsprüfungen gedacht. Der entsprechende Hinweis steht im
Profil selbst und erscheint bei `python3 profil.py`.

---

## Neues Profil anlegen

Kopieren Sie `edln.json` und passen Sie an:

```json
{
  "code": "EDLV",
  "name": "Niederrhein-Weeze",
  "lat": 51.6024,
  "lon": 6.1422,

  "radius_nm": 15.0,
  "max_alt_ft": 10000.0,
  "interval_s": 5.0,

  "low_ft": 2500.0,
  "overflight_km": 1.0,
  "view_km": 11.0,
  "platzrunde": true,

  "runways": [
    {"id": "09", "heading": 90},
    {"id": "27", "heading": 270}
  ],

  "orte": [
    {"name": "Weeze",  "lat": 51.6250, "lon": 6.1960},
    {"name": "Kevelaer","lat": 51.5830, "lon": 6.2460}
  ],

  "hinweis": "Freitext, erscheint in der Profilausgabe."
}
```

### Die Felder im Einzelnen

| Feld | Bedeutung |
|---|---|
| `code` / `name` | erscheinen in Report und Grafik |
| `lat` / `lon` | Flughafenbezugspunkt (ARP) |
| `radius_nm` | Erfassungsradius |
| `max_alt_ft` | blendet hohen Durchgangsverkehr aus |
| `interval_s` | Abfragetakt; bei viel Verkehr erhöhen |
| `low_ft` | Obergrenze „tief und damit laut" |
| `overflight_km` | Radius, ab dem ein Überflug zählt |
| `view_km` | halbe Kantenlänge der Karte |
| `platzrunde` | `false` bei Verkehrsflughäfen ohne Platzrundenbetrieb |
| `runways` | Liste mit `id` und **rechtweisendem** Kurs in Grad |
| `orte` | Anrainerlagen, die ausgewertet werden |

### Koordinaten beschaffen

- **Flugplatz:** `openAIP.net` oder `skyvector.com` → ARP ablesen
- **Ortslagen:** OpenStreetMap → Rechtsklick → „Adresse anzeigen" liefert
  Breite und Länge. Nehmen Sie die **Ortsmitte**, nicht das Ortsschild.

### Pistenkurs

Tragen Sie den **rechtweisenden** (true) Kurs ein, nicht den missweisenden.
Die Bahnbezeichnung ist gerundet-missweisend: RWY 13 hat in Mönchengladbach
rechtweisend 135°, in Düsseldorf hat RWY 05 rechtweisend 053° (nicht 050°).
Ein Fehler von wenigen Grad ist unkritisch — die Erkennung arbeitet mit
±30° Toleranz.

**Parallelbahnen** (05L/05R) haben denselben Kurs und sind aus der Flugspur
**nicht unterscheidbar**. Tragen Sie beide ein; die Auswertung fasst sie
automatisch zu einer Richtung zusammen und weist darauf hin.

---

## Prüfen, bevor Sie es ausrollen

```bash
docker exec flugspur-summary sh -c "TRACKER_PLATZ=edlv python3 /app/profil.py"
```

Das zeigt das wirksame Profil samt Entfernung jeder Ortslage vom Platz —
so fallen vertauschte Koordinaten sofort auf (ein Ort 80 km entfernt ist
ein Zahlendreher).

---

## Einstellungen übersteuern, ohne die Datei zu ändern

Umgebungsvariablen haben Vorrang vor dem Profil:

```yaml
environment:
  TRACKER_PLATZ: "edln"
  TRACKER_INTERVAL_S: "3"     # feiner als im Profil hinterlegt
  TRACKER_VIEW_KM: "20"       # größerer Kartenausschnitt
```

Reihenfolge: Vorgaben im Code → Profildatei → Umgebungsvariablen.

Das alte Präfix `EDLN_` funktioniert weiterhin, damit bestehende
Compose-Dateien nicht brechen. Für neue Installationen `TRACKER_` nutzen.

---

## Zwei Dinge, die bei großen Flughäfen anders sind

**Datenmenge.** Ein Stichprobenvergleich über jeweils 45 Sekunden ergab
15 Positionen für Mönchengladbach gegenüber 88 für Düsseldorf — grob das
Sechsfache, und das an einem ruhigen Abend. Tagsüber ist der Unterschied
größer. Erhöhen Sie `interval_s` auf 10 und begrenzen Sie `max_alt_ft`,
sonst wächst der Speicherbedarf schnell.

**Platzrundenerkennung ist sinnlos.** An Verkehrsflughäfen gibt es keinen
Schulflugbetrieb in der Platzrunde. Setzen Sie `"platzrunde": false` — die
Auswertung lässt den Block dann weg, statt irreführende Treffer zu melden.
