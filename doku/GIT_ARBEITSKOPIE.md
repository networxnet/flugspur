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

### 1. Repository auf GitHub anlegen

In GitHub Desktop: **File → Add local repository**, den entpackten
Projektordner wählen, dann **Publish repository**. Haken bei
*Keep this code private* setzen.

Die 14 bisherigen Commits bleiben dabei erhalten — die Entwicklung ist
von Anfang an nachvollziehbar.

### 2. Netzlaufwerk verbinden

Im Windows-Explorer: **Dieser PC → Netzlaufwerk verbinden**

```
\\<Adresse-des-NAS>\Container
```

Laufwerksbuchstabe zum Beispiel `Z:`. Anmeldedaten speichern lassen.

### 3. Arbeitskopie auf den Share klonen

In GitHub Desktop: **File → Clone repository → Local path**, und als
Ziel `Z:\flugspur-code` eintragen.

Der Ordner muss noch nicht existieren, GitHub Desktop legt ihn an. Er
muss aber **leer** sein — klonen in einen gefüllten Ordner lehnt Git ab.

### 4. Stack auf den neuen Pfad zeigen lassen

In Portainer: Stack `flugspur` → **Editor**. Die Pfade stehen jetzt als
Variablen in der Compose-Datei, Sie müssen nichts im Text ändern.
Tragen Sie unten unter **Environment variables** ein:

| name | value |
|---|---|
| `FS_APP_PFAD` | `/share/CACHEDEV1_DATA/Container/flugspur-code/app` |

`FS_DATA_PFAD` lassen Sie weg — die Vorgabe zeigt bereits auf
`/share/CACHEDEV1_DATA/Container/flugspur/data`, wo Ihre Daten liegen.

Dann **Update the stack**.

### 5. Prüfen

Monitor aufrufen. Steht dort „Überflüge heute · 1,5 km Umkreis" mit den
Spalten *tief* und *gesamt*, läuft der neue Stand aus der Arbeitskopie.

---

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
