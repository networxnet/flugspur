# Flugspur

**Zeichnet auf, wer wann wie tief über welchem Ort fliegt.**

Ein Werkzeug für Bürgerinitiativen: Es zeichnet Flugbewegungen rund um einen
Flugplatz auf und bereitet sie so auf, dass auch Nichtfachleute — Ratsmitglieder,
Presse, Nachbarschaft — sofort ein Bild bekommen.

**Keine Hardware. Keine Konten bei Datenanbietern. Keine Kosten.**

> Themen: `flugspur` `fluglärm` `ads-b` `ogn` `flarm` `bürgerinitiative`
> `lärmschutz` `platzrunde` `aircraft-tracking`
>
> *(Bitte nach dem Hochladen als GitHub-Topics eintragen — darüber finden
> andere Initiativen das Projekt.)*

---

## Was es tut

| Dienst | erfasst | Quelle |
|---|---|---|
| `adsb` | Motorflug, Geschäftsreiseflug, Mode-S per MLAT | adsb.fi, adsb.lol |
| `ogn` | Segelflug, Ultraleicht, Tragschrauber (FLARM/ADS-L) | Open Glider Network |
| `summary` | Auswertung auf Zuruf | lokal |

Heraus kommen ein Textreport, eine CSV-Tabelle und eine **eigenständige
HTML-Seite** mit Karte, Dichtekarte und Diagrammen: ohne Internet anzeigbar,
per Mail verschickbar, als PDF druckbar.

Die Auswertung beantwortet vier Fragen:

1. **Wo** wurde geflogen? Karte mit echten Spuren, eingefärbt nach Höhe —
   je röter, desto tiefer und lauter.
2. **Wo verdichtet** sich die Belastung? Dichtekarte der Tiefflüge.
3. **Welcher Ort** ist wie stark betroffen? Überflüge je Ortslage mit
   niedrigster gemessener Höhe.
4. **Wann und womit** wurde geflogen? Tagesgang und Musterspektrum.

---

## Platzunabhängig

Alles Ortsspezifische steckt in einem Profil unter `app/plaetze/<kürzel>.json` —
Lage, Pisten, Anrainerorte, Schwellenwerte. Ein weiterer Flugplatz ist eine
JSON-Datei, keine Codeänderung.

```yaml
environment:
  TRACKER_PLATZ: "edln"
```

Mitgeliefert: `edln` (Mönchengladbach) und `eddl` (Düsseldorf).
Anleitung: [`doku/NEUER_FLUGPLATZ.md`](doku/NEUER_FLUGPLATZ.md)

Mehrere Plätze parallel mitschneiden? Stack zweimal ausrollen und die
Variable `STACK` unterschiedlich setzen (`STACK=fs-edln`, `STACK=fs-eddl`) —
die Containernamen richten sich danach.

---

## Schnellstart (Portainer)

```yaml
# Stacks -> Add stack -> Web editor -> docker-compose.image.yml einfuegen
# Environment variables:
#   FS_IMAGE       ghcr.io/<IHR-NAME>/flugspur:latest
#   FS_DATA_PFAD   /share/Container/flugspur/data
#   TRACKER_PLATZ  edln
```

Anleitungen in [`doku/`](doku/):

- [`INSTALLATION_QNAP.md`](doku/INSTALLATION_QNAP.md) — Einrichtung Schritt für Schritt, rein grafisch
- [`INSTALLATION_IMAGE.md`](doku/INSTALLATION_IMAGE.md) — Weg über GitHub und eigenes Image
- [`BEDIENUNG.md`](doku/BEDIENUNG.md) — Alltag: kontrollieren, auswerten, exportieren
- [`NEUER_FLUGPLATZ.md`](doku/NEUER_FLUGPLATZ.md) — weiteren Platz einrichten
- [`ENTSCHEIDUNG_IMAGE_ODER_MOUNT.md`](doku/ENTSCHEIDUNG_IMAGE_ODER_MOUNT.md) — warum es zwei Varianten gibt

---

## Einstellungen

| Variable | Bedeutung |
|---|---|
| `TRACKER_PLATZ` | **Profil wählen**, z. B. `edln` |
| `TRACKER_PROFIL` | alternativ: Pfad zu eigener JSON-Datei |
| `TRACKER_RADIUS_NM` | Erfassungsradius |
| `TRACKER_MAX_ALT_FT` | blendet hohen Durchgangsverkehr aus |
| `TRACKER_INTERVAL_S` | Abfragetakt |
| `TRACKER_OVERFLIGHT_KM` | Radius, ab dem ein Überflug zählt |
| `TRACKER_LOW_FT` | Obergrenze „tief und laut" |
| `TRACKER_VIEW_KM` | halbe Kantenlänge der Karte |

Reihenfolge: Vorgaben im Code → Profildatei → Umgebungsvariablen.
Wirksames Profil anzeigen: `python3 /app/profil.py`

Datenmenge: etwa **40–80 MB pro Monat** an einem kleinen Platz.

---

## Vor dem Einsatz prüfen: gibt es schon amtliche Daten?

Diese Frage ist wichtiger als die Technik. An großen Verkehrsflughäfen
existieren oft **bessere** Quellen als alles, was dieses Werkzeug liefern kann:

| Quelle | bietet |
|---|---|
| Lärmportal des Flughafens (z. B. TraVis in Düsseldorf) | kalibrierte Lärmpegel, Flugplandaten, Historie |
| DFS STANLY_Track | 14 Tage Radarspuren in amtlicher Qualität |
| Deutscher Fluglärmdienst (dfld.de) | lange Historie, teils mit Messstellen |

**Flugspur lohnt dort, wo es nichts davon gibt** — an kleinen Plätzen
ohne Portal, ohne Messstellen und ohne Transponderpflicht. Mönchengladbach
ist genau so ein Fall; Düsseldorf ausdrücklich nicht. Das mitgelieferte
`eddl.json` dient Quervergleichen, nicht dem Ersatz von TraVis.

---

## Technisches

Reine Python-Standardbibliothek — kein `pip install`, keine Lieferkette, die
brechen kann. Das Image enthält **keinen einzigen `RUN`-Befehl**, dadurch
entstehen amd64 und arm64 ohne Emulation in Sekunden. Es läuft
unprivilegiert unter UID 1000. Läuft auf NAS, Linux-Server und Raspberry Pi.

---

## Grenzen — bitte mitlesen und mitzitieren

Erfasst werden nur Luftfahrzeuge mit **ADS-B, MLAT-fähigem Mode-S oder
FLARM/ADS-L**. An vielen kleinen Plätzen, auch in Mönchengladbach, besteht
**keine Transponderpflicht**. Maschinen mit reinem Mode-A/C-Gerät bleiben
unsichtbar.

**Alle Stückzahlen sind damit Untergrenzen:** Es war mindestens so viel
Verkehr, nie weniger. Für Aussagen zur Spurtreue der erfassten Flüge ist das
unerheblich, für absolute Bewegungszahlen nicht.

Ein Überflug über eine Ortslage ist zudem **für sich genommen kein
Rechtsverstoß**. Freiwillige Vereinbarungen zur Lärmminderung sind vielerorts
nicht rechtsverbindlich, und Mindestflughöhen bestehen nicht überall.
Flugspur belegt das **tatsächliche Ausmaß** der Belastung — nicht ein
Fehlverhalten einzelner Piloten.

Wer diese beiden Absätze in Veröffentlichungen mitführt, nimmt der Gegenseite
ihr wirksamstes Argument vorweg. Das ist kein Eingeständnis von Schwäche,
sondern der Grund, warum die übrigen Zahlen belastbar sind.

---

## Lizenz

MIT — gerne weitergeben und anpassen. Ausdrücklich auch für andere
Bürgerinitiativen gedacht.
