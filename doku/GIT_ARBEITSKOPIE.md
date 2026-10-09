# Änderungen ohne Hochladen — der Share als Git-Arbeitskopie

Ziel: Ich committe eine Korrektur, Sie klicken einmal in GitHub Desktop,
und die Dateien liegen im selben Moment auf dem NAS. Kein Hochladen
einzelner Dateien mehr, und jederzeit nachvollziehbar, welcher Stand
wann lief.

Auf dem NAS muss dafür **nichts** installiert werden.

---

## Der Aufbau

Zwei getrennte Ordner, das ist der entscheidende Punkt:

```
/share/CACHEDEV1_DATA/Container/
├── flugspur-code/        <- Git-Arbeitskopie, wird überschrieben
│   ├── app/
│   ├── doku/
│   └── docker-compose.qnap.yml
└── flugspur/
    └── data/             <- Ihre Mitschnitte, Git fasst das nie an
```

**Warum getrennt?** Git darf nur den Programmcode verwalten. Würden die
Mitschnitte im selben Ordner liegen, könnte ein unbedachtes
Zurücksetzen auf einen älteren Stand Messdaten löschen. Der Ordner
`flugspur/data` bleibt genau dort, wo er heute ist — die laufende
Aufzeichnung wird durch die Umstellung nicht unterbrochen.

---

## Einrichtung, einmalig

Kürzester Weg: Das Projekt landet direkt auf dem Share und wird von dort
veröffentlicht. So entsteht nur **eine** Arbeitskopie, nicht zwei.

### 1. Netzlaufwerk verbinden

Windows-Explorer → **Dieser PC** → **Netzlaufwerk verbinden**

```
\\<Adresse-des-NAS>\Container
```

Buchstabe zum Beispiel `Z:`, Anmeldedaten speichern lassen. Sie sollten
darin den vorhandenen Ordner `flugspur` sehen — dann stimmt die Freigabe.

### 2. Paket entpacken

`flugspur-mit-historie.zip` nach

```
Z:\flugspur-code
```

entpacken. Achten Sie darauf, dass **kein doppelter Ordner** entsteht:
In `Z:\flugspur-code` müssen direkt `app`, `doku`, `README.md` und der
versteckte Ordner `.git` liegen — nicht noch ein Unterordner `flugspur`.

Falls Sie `.git` nicht sehen: Im Explorer unter **Ansicht** die
*ausgeblendeten Elemente* einschalten. Ohne diesen Ordner fehlt die
Versionsgeschichte, und GitHub Desktop erkennt das Projekt nicht.

### 3. In GitHub Desktop aufnehmen

**File → Add local repository**, Ordner `Z:\flugspur-code` wählen.

Erscheint die Meldung, dies sei kein Git-Repository, wurde das Paket
falsch entpackt — zurück zu Schritt 2.

Unter **History** müssen jetzt **15 Commits** stehen, der oberste
beginnt mit „Monitor: Auswertungsknoepfe".

### 4. Veröffentlichen

**Publish repository**. Name `flugspur`, Haken bei
**Keep this code private** setzen. Bestätigen.

Damit liegt die vollständige Entwicklungsgeschichte auf GitHub, und ich
kann Ihnen künftig Änderungen über dieses Repository zukommen lassen.

### 5. Stack auf den neuen Pfad zeigen lassen

In Portainer: Stack `flugspur` → **Editor**. Im Text ändern Sie nichts;
tragen Sie unten unter **Environment variables** ein:

| name | value |
|---|---|
| `FS_APP_PFAD` | `/share/CACHEDEV1_DATA/Container/flugspur-code/app` |

`FS_DATA_PFAD` weglassen — die Vorgabe zeigt bereits auf
`/share/CACHEDEV1_DATA/Container/flugspur/data`, wo Ihre Mitschnitte
liegen. Dann **Update the stack**.

### 6. Prüfen

Monitor aufrufen. Drei Dinge müssen jetzt anders aussehen:

- Überschrift **„Überflüge heute · 1,5 km Umkreis"** statt 1 km
- zwei Spalten **tief** und **gesamt**
- die Auswertungsknöpfe als gruppierte Schaltflächen statt als Textlinks

Stimmt das, läuft der Stack aus der Arbeitskopie und das Hochladen
einzelner Dateien hat ein Ende.

### 7. Den alten Programmordner aufräumen

Erst wenn Schritt 6 geklappt hat: Der alte Ordner
`Container/flugspur/app` wird nicht mehr gebraucht. Lassen Sie ihn ein
paar Tage als Rückfallebene liegen, dann löschen Sie ihn.

**`Container/flugspur/data` bleibt.** Dort liegen Ihre Mitschnitte.

## Der Alltag danach

Ich committe eine Änderung und sage Ihnen Bescheid. Sie machen:

1. GitHub Desktop öffnen → **Fetch origin** → **Pull origin**
2. In Portainer den betroffenen Container neu starten
   (meist nur `flugspur-monitor`)

Das war alles. Die Dateien auf dem NAS sind in dem Moment aktuell, in
dem der Pull durchläuft.

**Einen Neustart braucht es trotzdem**, weil Python den Code beim Start
einliest. Geänderte Platzprofile (`plaetze/*.json`) wirken dagegen
sofort, die werden bei jedem Durchlauf neu gelesen.

---

## Zurück auf einen früheren Stand

Der eigentliche Gewinn. In GitHub Desktop unter **History** sehen Sie
jeden Commit. Rechtsklick auf einen älteren Eintrag →
**Revert changes in commit** macht genau diese eine Änderung rückgängig,
ohne die späteren zu verlieren.

Für die Auswertung ist das mehr als Bequemlichkeit: Sie können später
belegen, mit welcher Programmfassung eine Messung entstanden ist.

---

## Was dabei zu beachten ist

**Zeilenenden.** Die beiliegende `.gitattributes` erzwingt LF. Ohne sie
schreibt Windows CRLF in die Dateien. Python stört das nicht, aber es
erzeugt bei jedem Pull unnötige Unterschiede.

**Niemals direkt auf dem Share editieren.** Änderungen, die Sie dort von
Hand machen, kollidieren beim nächsten Pull. Wenn etwas anzupassen ist,
sagen Sie es mir, dann kommt es sauber als Commit.

**Der Ordner `.git` liegt mit auf dem Share.** Er ist klein (unter einem
Megabyte) und stört nicht. Die Container sehen ihn nicht, weil nur der
Unterordner `app` eingebunden wird.

**Die Mitschnitte bleiben unberührt.** `data/` steht in `.gitignore`.
Selbst ein vollständiges Zurücksetzen der Arbeitskopie fasst sie nicht
an — sie liegen in einem anderen Ordner.

---

## Später: Umstieg auf versionierte Images

Wenn zwei Wochen stabil gelaufen sind, lohnt der zweite Schritt. Dann
baut GitHub Actions bei jedem Commit ein fertiges Image mit
Versionsnummer, und Portainer zieht `:v1.3` statt eines Dateistands.
Die Vorbereitung liegt in `.github/workflows/build.yml` bereit,
beschrieben in `doku/INSTALLATION_IMAGE.md`.

Für die jetzige Phase wäre das hinderlich: Jede Änderung dauert dann
fünf bis zehn Minuten statt Sekunden.
