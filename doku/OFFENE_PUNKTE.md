# Offene Punkte

Diese Datei hält fest, was noch zu tun ist und **warum**. Sie existiert,
damit wichtige Erkenntnisse nicht in Gesprächen versickern.

Reihenfolge nach Bedeutung für die Leitfrage: *Inwiefern sind Anwohner
stärker von Flugverkehr und -lärm betroffen, und halten sich Piloten an die
Regularien?*

---

## 1. Platzrundentreue messen — HOHE PRIORITÄT, jetzt umsetzbar

**Warum das der wichtigste offene Punkt ist**

Das **Landesumweltamt Brandenburg** hat an mehreren Verkehrslandeplätzen die
tatsächlich geflogenen Platzrunden optisch und laseroptisch vermessen
(Studien und Tagungsberichte Band 43, 2003, Abschnitt 3.2.2). Die
Ergebnisse:

* Es wurden **systematische Abweichungen** von der vorgeschriebenen
  Platzrunde festgestellt — keine zufällige Streuung.
* Die Abweichung **wächst mit dem Abstand vom Abrollpunkt**.
* Sie verlagert sich in Flugrichtung gesehen systematisch **nach außen**,
  also aus der Platzrunde heraus und damit in Richtung der Ortslagen.
* Nach der **vierten Kurve** erreicht der Schwerpunkt der Abweichung mit
  **fast 500 m** sein Maximum. Einzelne Messwerte lagen über **1.400 m**
  neben der Soll-Linie.
* Im **Endanflug** ist die Abweichung nahezu null — dort wird genau
  geflogen, weil die Bahn in Sicht ist.

Die Studie zieht daraus eine Folgerung, die für die Bürgerinitiative
unmittelbar verwertbar ist:

> Werden systematische Abweichungen von der vorgeschriebenen Flugstrecke
> Platzrunde festgestellt, muss der Flugplatzbetreiber durch die zuständige
> Behörde beauftragt werden, die Einhaltung der festgelegten Platzrunde am
> Flugplatz zu gewährleisten.

**Damit ist die Fragestellung amtlich anerkannt und methodisch etabliert.**
Wir erfinden nichts Neues, sondern wiederholen eine Untersuchung, die ein
Landesumweltamt selbst für geboten hält — nur mit besserer Datenlage, weil
wir nicht an zwei Messstellen für ein paar Tage stehen, sondern dauerhaft
jede empfangbare Position aufzeichnen.

Das Muster passt außerdem zur Lage in Schiefbahn-Unterbruch: Die Abweichung
nach außen ist dort am größten, wo die Platzrunde ohnehin am nächsten an die
Bebauung heranführt.

### Soll-Platzrunde — BESCHAFFT

Die empfohlene Platzrunde EDLN liegt seit dem 10.10.2026 als Geometrie im
Platzprofil unter `platzrunde_geometrie`:

| Runde | Höhe | Lage | Punkte | Länge |
|---|---|---|---|---|
| Nordplatzrunde | 1.200 ft MSL | nordöstlich der Bahn | 40 | 11,5 km |
| Südplatzrunde | 1.100 ft MSL | südwestlich der Bahn | 25 | 7,8 km |

**Herkunft:** Der Flughafen Mönchengladbach veröffentlicht die empfohlene
Platzrunde auf seiner Website, nicht im amtlichen Anflugblatt. Der
Aeroclub 77 stellt dieselbe Darstellung als Kartendienst bereit, aus dem
sich die Koordinaten exakt exportieren ließen. Die Rohdatei liegt unter
`doku/belege/platzrunde_edln.geojson`.

**Wichtiger Vorbehalt, wörtlich aus der Quelle:** *Vorbehaltlich
anderslautender Anweisungen durch die Platzkontrollstelle (TWR) gilt diese
Platzrundendarstellung nur als Empfehlung.* Der Flughafen nennt selbst drei
Gründe für zulässige Abweichungen: unterschiedliche Leistungsdaten der
Luftfahrzeuge, Ausbildungsstand des Piloten samt genehmigter Abweichungen
zu Ausbildungszwecken, sowie Wetter- und Sichtbedingungen.

Dass die Platzrunde **nicht im amtlichen Anflugblatt** steht, ist ein
eigener Befund: Ein ortsfremder Pilot findet sie nur, wenn er die Website
des Flughafens kennt. In Pilotenforen wird genau darauf hingewiesen.

### Was die Soll-Platzrunde über die Ortslagen verrät

Kürzester seitlicher Abstand der empfohlenen Runden zur jeweiligen
Ortslage:

| Ortslage | Nordplatzrunde | Südplatzrunde |
|---|---|---|
| Willich-Schiefbahn | **100 m** | 2.300 m |
| Willich-Neersen | 200 m | 500 m |
| MG-Damm/Uedding | 600 m | 200 m |
| Schiefbahn-Unterbruch | 600 m | 2.700 m |
| Korschenbroich-Raderbroich | 1.300 m | 300 m |
| Korschenbroich-Herrenshoff | 1.500 m | **0 m** |
| MG-Neuwerk | 2.200 m | 600 m |

Zwei Dinge springen ins Auge. Die **Nordplatzrunde streift Schiefbahn auf
100 m** — dort genügt schon eine kleine Abweichung nach außen, um über die
Bebauung zu kommen. Und die **Südplatzrunde führt direkt über
Herrenshoff**.

Zur Einordnung: Bei 1.200 ft MSL, also rund 355 m über Grund, ergibt die
Pegelabschätzung für ein Propellerflugzeug bis 2 t

| seitlicher Abstand | geschätzter Maximalpegel |
|---|---|
| 0 m (direkt darüber) | 70 dB(A) |
| 500 m | 64 dB(A) |
| 1.000 m | 58 dB(A) |
| 1.500 m | 54 dB(A) |

Eine Abweichung von 500 m nach außen — der Wert, den das Landesumweltamt
Brandenburg nach der vierten Kurve als Schwerpunkt gemessen hat — macht
also an einer 500 m entfernten Ortslage den Unterschied zwischen 64 und
70 dB(A). Das ist der Kern der ganzen Fragestellung.

### Vorgeschlagenes Vorgehen

1. Soll-Platzrunde als Punktliste in `app/plaetze/edln.json` aufnehmen,
   analog zu den Ortslagen — eine Liste je Betriebsrichtung.
2. **Messquerschnitte** definieren, analog zu den Punkten P1 bis P5 der
   Brandenburger Studie: Gegenanflug, Querabflug, nach jeder Kurve,
   Endanflug. Je Querschnitt eine Linie senkrecht zur Soll-Strecke.
3. Für jede Flugspur, die als Platzrunde erkannt wurde, den **vorzeichen-
   behafteten Abstand** zur Soll-Linie am jeweiligen Querschnitt bestimmen.
   Vorzeichen so wählen, dass **positiv „nach außen"** bedeutet — sonst ist
   das Ergebnis nicht mit Brandenburg vergleichbar.
4. Ausgeben: Mittelwert, Median, Streuung und Verteilung je Querschnitt,
   dazu die **Korridorbreite** nach `b = 4,8 · Streuung`.
5. Darstellen als Punktwolke je Querschnitt, wie in der Brandenburger
   Studie — damit die Zahlen direkt nebeneinandergelegt werden können.
6. **Vergleichswert ausweisen:** rund 500 m Schwerpunkt nach der vierten
   Kurve. Liegt EDLN darüber, ist das belegbar auffällig; liegt es darunter,
   muss das genauso berichtet werden.

### Fallstricke

* Die Platzrundenerkennung in `summary.py` arbeitet bisher über Nähe, tiefe
  Höhe und Dauer. Sie ist **nicht** daraufhin geprüft, ob sie weit außen
  geflogene Runden noch als Platzrunde erkennt. Wenn gerade die Ausreißer
  durchs Raster fallen, misst man systematisch zu brav. **Vor der Auswertung
  gegen Sichtbeobachtung prüfen.**
* Abweichung ist **kein Rechtsverstoß** — die Platzrunde an EDLN beruht auf
  einer Empfehlung des Lärmschutzbeirats, nicht auf einer verbindlichen
  Festlegung. Das muss bei jeder Darstellung dabeistehen.
  Siehe `METHODIK.md`, Abschnitt 3.4.

---

## 2. Wochengang und Wochenendanteil auswerten

Die Brandenburger Studie stellt fest, dass an Verkehrslandeplätzen das
Maximum der Flugbewegungen regelmäßig auf das **Wochenende** fällt — also
auf die Zeit mit der höchsten Störwirkung, weil Anwohner dann Ruhe im Freien
suchen. Sie verwendet deshalb ausdrücklich die **Wochenendtage der sechs
verkehrsreichsten Monate** als Kennzeichnungszeit.

Zu tun: Flugbewegungen je Wochentag und je Stunde auswerten, Wochenendanteil
ausweisen, mit dem Brandenburger Befund vergleichen. Die Daten dafür liegen
bereits vor; es fehlt nur die Auswertung.

---

## 3. Anteil Platzrundenflüge am Gesamtaufkommen

Derselben Studie zufolge sind an Verkehrslandeplätzen **etwa die Hälfte**
der Bewegungen Platzrundenflüge, an einzelnen Plätzen bis zu zwei Drittel.
Für EDLN wird von der Bürgerinitiative ein Schulflug-Anteil von über 50 %
genannt. Das lässt sich aus unseren Daten prüfen und beziffern.

---

## 3b. MLAT-Genauigkeit empirisch bestimmen

Fast alle Kleinflugzeuge werden per Multilateration geortet (siehe
`METHODIK.md`, Abschnitt 8b). Wie genau das ist, wissen wir nicht —
wir vermuten es nur.

Es gibt aber eine saubere Messmöglichkeit: Luftfahrzeuge, die **gleichzeitig
im Open Glider Network** erscheinen, liefern dort eine GPS-gestützte und
damit genaue Position. Der Abstand zwischen beiden Positionen zum selben
Zeitpunkt ist der MLAT-Fehler.

Zu tun: Meldungen beider Quellen über Zeit und Kennzeichen paaren, den
Abstand bilden, Verteilung und Median ausweisen. Damit ließe sich in der
Methodik eine **belegte Zahl** statt einer Vermutung angeben.

Dafür wird die OGN-Datei desselben Tages gebraucht.

---

## 4. Äquivalenter Dauerschallpegel

Gutachten beurteilen primär über den **äquivalenten Dauerschallpegel**, nicht
über Einzelereignisse. Aus unseren Ereignissen ließe sich ein Tageswert je
Ortslage abschätzen. Das wäre die Kenngröße, mit der Behörden rechnen —
allerdings mit erheblicher Unsicherheit, weil wir die Ereignisdauer nicht
messen, sondern nur den Maximalpegel schätzen. Vor der Umsetzung klären, ob
der Gewinn an Anschlussfähigkeit die zusätzliche Unsicherheit rechtfertigt.

---

## 5. Häufigkeits-Maximalpegelkriterium (NAT)

Die Form „sechs mal 65 dB(A)" aus dem Fluglärmgesetz: nicht nur zählen,
sondern prüfen, ob eine Schwelle regelmäßig öfter als n-mal am Tag
überschritten wird. Aus den vorhandenen Ereignissen unmittelbar ableitbar.

---

## 6. Bezugspegel gegen die DIN-Datenblätter abgleichen

Unsere Bezugspegel sind aus den Oktavpegeln der Landeplatz-Leitlinie
hergeleitet und gegen die Zulassungsgrenzwerte der LSL gegengeprüft
(`METHODIK.md`, Abschnitt 5.1). Ein Abgleich mit den Datenblättern des
Anhangs A der DIN 45684-1 wäre trotzdem wünschenswert. Die Norm ist
kostenpflichtig; möglicher Zugang über eine Hochschulbibliothek, das
Umweltamt der Stadt oder ein mit der BI zusammenarbeitendes Büro.

---

## 7. Betrieb und Ausrollung

* **GitHub-Veröffentlichung**: Zugangstoken fehlt, es gibt keinen
  Schreibzugriff. Die Auslieferung erfolgt bis auf Weiteres als
  `flugspur-mit-historie.zip` mit vollständiger `.git`-Historie.
* **Automatischer Start** der Auswertung (täglich, wöchentlich) ist noch
  nicht eingerichtet.
* **Verwaiste Container** `edln-*` auf der QNAP prüfen und entfernen.
* **Testplan Tag 2** (`TESTPLAN.md`) ist noch nicht abgearbeitet: eine halbe
  Stunde bei Sichtflugwetter mitzählen und mit der Erfassung vergleichen.
  Das ist die einzige echte Kontrolle der Erfassungsquote — und
  Voraussetzung dafür, die Untergrenze beziffern zu können.
  **Den Termin nicht raten:** `python3 /app/beste_zeit.py --fenster 60`
  sucht aus den bereits aufgezeichneten Daten das Zeitfenster mit den
  meisten Bewegungen heraus und nennt die zu erwartende Stückzahl. Je
  dichter der Betrieb, desto kürzer muss man vor Ort stehen.
