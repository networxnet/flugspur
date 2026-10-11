# Änderungen ohne Hochladen — der Share als Git-Arbeitskopie

Ziel: Ich committe eine Korrektur, Sie klicken einmal in GitHub Desktop,
und die Dateien liegen im selben Moment auf dem NAS. Kein Hochladen
einzelner Dateien mehr, und jederzeit nachvollziehbar, welcher Stand
wann lief.

Auf dem NAS muss dafür **nichts** installiert werden.

---

## Der Aufbau

Ein Ordner `flugspur`, darin zwei klar getrennte Bereiche:

```
/share/CACHEDEV1_DATA/Container/flugspur/
├── repo/     <- Git-Arbeitskopie, wird bei jedem Update überschrieben
│   ├── app/
│   ├── doku/
│   └── docker-compose.qnap.yml
└── data/     <- Ihre Mitschnitte, Git fasst das nie an
```

Der Container bindet `repo/app` schreibgeschützt als `/app` ein und
`data` als `/data`.

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
Z:\flugspur\repo
```

entpacken. Achten Sie darauf, dass **kein doppelter Ordner** entsteht:
In `Z:\flugspur\repo` müssen direkt `app`, `doku`, `README.md` und der
versteckte Ordner `.git` liegen — nicht noch ein Unterordner `flugspur`.

Falls Sie `.git` nicht sehen: Im Explorer unter **Ansicht** die
*ausgeblendeten Elemente* einschalten. Ohne diesen Ordner fehlt die
Versionsgeschichte, und GitHub Desktop erkennt das Projekt nicht.

### 3. In GitHub Desktop aufnehmen

**File → Add local repository**, Ordner `Z:\flugspur\repo` wählen.

Erscheint die Meldung, dies sei kein Git-Repository, wurde das Paket
falsch entpackt — zurück zu Schritt 2.

Unter **History** muss die vollständige Versionsgeschichte stehen. Zeigt
GitHub Desktop stattdessen an, dies sei kein Repository, fehlt der Ordner
`.git` — zurück zu Schritt 2.

### 4. Veröffentlichen

**Publish repository**. Name `flugspur`. Soll das Projekt öffentlich
nachvollziehbar sein — was bei einer Methodendokumentation der Sinn der
Sache ist —, den Haken bei **Keep this code private** *entfernen*.

Damit liegt die vollständige Entwicklungsgeschichte auf GitHub, und ich
kann Ihnen künftig Änderungen über dieses Repository zukommen lassen.

### 5. Stack auf den neuen Pfad zeigen lassen

In Portainer: Stack `flugspur` → **Editor**. Im Text ändern Sie nichts;
tragen Sie unten unter **Environment variables** ein:

| name | value |
|---|---|
| `FS_APP_PFAD` | `/share/CACHEDEV1_DATA/Container/flugspur/repo/app` |

`FS_DATA_PFAD` weglassen — die Vorgabe zeigt bereits auf
`/share/CACHEDEV1_DATA/Container/flugspur/data`, wo Ihre Mitschnitte
liegen. Dann **Update the stack**.

### 6. Prüfen

    python3 /app/selbsttest.py

Muss „BESTANDEN" melden. Zusätzlich im Monitor nachsehen, ob die
Lärmereignisse mit Pegelschwellen angezeigt werden (`ab 55 dB(A)` und
`ab 65 dB(A)`). Stimmt das, läuft der Stack aus der Arbeitskopie und das
Hochladen einzelner Dateien hat ein Ende.

### 7. Den alten Programmordner aufräumen

Erst wenn Schritt 6 geklappt hat: Der alte Ordner
`Container/flugspur/app` wird nicht mehr gebraucht — sein Inhalt steckt
jetzt in `repo/app`. Lassen Sie ihn ein paar Tage als Rückfallebene
liegen, dann löschen Sie ihn.

**`Container/flugspur/data` bleibt unangetastet.** Dort liegen Ihre
Mitschnitte. Git fasst diesen Ordner nie an, weil er außerhalb der
Arbeitskopie liegt — das ist der ganze Grund für diesen Aufbau.

## Der Alltag danach

**Sie machen nichts.**

Im Stack läuft ein Dienst `aktualisierer`, der alle 15 Minuten
`git pull` ausführt. Die übrigen Dienste merken, dass der Code getauscht
wurde, beenden sich und werden von Docker mit dem neuen Stand neu
gestartet. Spätestens eine Viertelstunde nach meinem Commit läuft bei
Ihnen der neue Code.

Soll es sofort gehen: im Container `flugspur-aktualisierer` einmal
`git -C /repo pull` ausführen, oder den Container neu starten.

Von Hand geht es natürlich weiterhin:

    cd /share/CACHEDEV1_DATA/Container/flugspur/repo
    git pull

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


---

## Umstellung eines bestehenden Aufbaus

Wer bisher die Dateien von Hand nach `Container/flugspur/app` kopiert hat,
stellt einmalig um. Der Aufwand sind fünf Minuten, danach entfällt das
Kopieren dauerhaft.

1. **Stack anhalten** (Portainer → Stack `flugspur` → *Stop*). Sonst
   arbeitet der Container mitten im Austausch mit halben Dateien.

2. **Arbeitskopie holen.** Auf der NAS per SSH:

        cd /share/CACHEDEV1_DATA/Container/flugspur
        git clone https://github.com/networxnet/flugspur.git repo

   Der Zielordner heißt ausdrücklich `repo`. Ohne diese Angabe legt Git
   einen Ordner `flugspur` an — und der kollidiert mit dem darüber
   liegenden.

   Ohne SSH-Zugang: `flugspur-mit-historie.zip` in `…/flugspur/repo`
   entpacken, `.git` muss mitkommen.

3. **Pfad in Portainer ändern.** Beim Stack unter *Environment variables*:

   | Variable | Wert |
   |---|---|
   | `FS_APP_PFAD` | `/share/CACHEDEV1_DATA/Container/flugspur/repo/app` |

   `FS_DATA_PFAD` bleibt unverändert. Dann **Update the stack**.

4. **Prüfen:** `python3 /app/selbsttest.py`

5. **Alten Ordner** `Container/flugspur/app` nach ein paar Tagen löschen.

Der Ordner `data` wird dabei zu keinem Zeitpunkt angefasst. Die
Aufzeichnung läuft weiter, und alle bisherigen Tage bleiben auswertbar.


---

## Wie die automatische Aktualisierung funktioniert

Drei Teile greifen ineinander:

**Der Dienst `aktualisierer`** (Abbild `alpine/git`) hat die Arbeitskopie
unter `/repo` eingebunden und führt in einer Schleife `git pull --ff-only`
aus. Er fasst sonst nichts an und hat keinen Zugriff auf den Docker-Dienst.

**`app/neustart.py`** bildet beim Start eine Kennzahl über alle
Python-Dateien in `/app`. Die Dauerprozesse prüfen diese Kennzahl
regelmäßig. Hat sie sich geändert, beenden sie sich mit Rückgabewert 0.

**`restart: unless-stopped`** sorgt dafür, dass Docker sie sofort wieder
startet — und dabei den neuen Code einliest.

Kein Docker-Socket, keine erhöhten Rechte, kein Dienst, der andere
Container steuert. Jeder Prozess entscheidet für sich.

### Die zwei Sicherungen

**Fehlerhafter Code wird nicht übernommen.** Vor dem Neustart wird jede
Datei übersetzt. Scheitert das, läuft der Prozess mit dem alten, noch im
Speicher liegenden Stand weiter und meldet den Fehler im Protokoll. Ein
Tippfehler im Repository kann die Aufzeichnung also nicht stoppen.

**Halbe Stände werden abgewartet.** Erst wenn sich 20 Sekunden lang
nichts mehr geändert hat, wird neu gestartet. Sonst erwischt man einen
`git pull` mitten im Schreiben.

### Einstellungen

| Variable | Vorgabe | Bedeutung |
|---|---|---|
| `FS_UPDATE_S` | `900` | Abstand zwischen zwei `git pull` in Sekunden |
| `FS_REPO_PFAD` | `…/Container/flugspur/repo` | Arbeitskopie, vom Aktualisierer beschreibbar |

**`FS_UPDATE_S=0` schaltet die Automatik ab.** Sinnvoll, wenn Sie eine
Messreihe fahren und während dieser Zeit keinen Code-Wechsel wollen.

### Einmalig nötig

Der Dienst ist neu, deshalb muss die Stack-Definition in Portainer einmal
aktualisiert werden: Compose-Datei neu einlesen beziehungsweise den Inhalt
von `docker-compose.qnap.yml` ersetzen, `FS_REPO_PFAD` setzen, **Update
the stack**. Danach ist Schluss mit dem Kopieren.
