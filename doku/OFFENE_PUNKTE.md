# Offene Punkte

Diese Datei hält fest, was noch zu tun ist und **warum**. Sie existiert,
damit wichtige Erkenntnisse nicht in Gesprächen versickern.

Reihenfolge nach Bedeutung für die Leitfrage: *Inwiefern sind Anwohner
stärker von Flugverkehr und -lärm betroffen, und halten sich Piloten an die
Regularien?*

---

## 1. Platzrundentreue messen — HOHE PRIORITÄT

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

### Was dafür fehlt

**Die Soll-Platzrunde als Geometrie.** Im Platzprofil ist `platzrunde`
bisher nur ein Ja/Nein-Schalter, der die Platzrundenerkennung einschaltet.
Es gibt keinen Linienzug, gegen den gemessen werden könnte.

Zu beschaffen: die Platzrunde EDLN aus der **Sichtanflugkarte** (AIP VFR
beziehungsweise die Veröffentlichung des Flugplatzes), getrennt für beide
Betriebsrichtungen (13 und 31) und, falls vorhanden, getrennt nach
Luftfahrzeugart. Dazu die **festgelegte Platzrundenhöhe**.

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
