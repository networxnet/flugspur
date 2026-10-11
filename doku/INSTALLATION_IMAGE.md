# Weg B: Geschlossenes Image über GitHub — Schritt für Schritt

Komplett im Browser. Kein Build-Rechner, kein SSH, keine Kommandozeile.
**Rund 30 Minuten.**

Ergebnis: ein versioniertes Image unter `ghcr.io/networxnet/flugspur`,
das auf QNAP, Synology, Unraid und Raspberry Pi identisch läuft — und das
Sie an andere Initiativen weitergeben können.

---

## Schritt 1 — Repository anlegen (3 Min)

1. github.com → oben rechts **+** → **New repository**
2. **Repository name:** `flugspur`
3. **Public** auswählen
   *(Private ginge auch, dann muss aber das Paket später trotzdem öffentlich
   gestellt werden — Public ist der einfachere Weg.)*
4. Haken bei „Add a README file" **weglassen** — wir bringen eine eigene mit
5. **Create repository**

---

## Schritt 2 — Dateien hochladen (10 Min)

Entpacken Sie `flugspur.zip` auf Ihrem Rechner. Sie sehen:

```
flugspur/
├── app/                      5 Python-Dateien
├── .github/workflows/        build.yml
├── doku/                     Anleitungen
├── Dockerfile
├── docker-compose.image.yml
├── docker-compose.qnap.yml
├── docker-compose.pfadtest.yml
├── README.md
├── LICENSE
└── .gitignore
```

Im leeren Repository: **uploading an existing file** anklicken. Dann
**den gesamten Inhalt** des entpackten Ordners in das Browserfenster ziehen
— nicht den Ordner selbst, sondern seinen Inhalt. GitHub übernimmt die
Unterordner automatisch.

Unten **Commit changes**.

> **Prüfen Sie zwei Dinge**, bevor Sie weitermachen:
> - Liegt `README.md` in der Wurzel (nicht in einem Unterordner)?
> - Existiert der Pfad `.github/workflows/build.yml`?
>
> Ordner, deren Name mit einem Punkt beginnt, werden von manchen
> Entpackprogrammen **ausgeblendet**. Fehlt `.github`, läuft später kein
> Build. Im Zweifel: **Add file → Create new file**, als Namen exakt
> `.github/workflows/build.yml` eintippen (GitHub legt die Ordner dabei
> selbst an) und den Inhalt der Datei hineinkopieren.

---

## Schritt 3 — Actions Schreibrechte geben (2 Min)

**Ohne diesen Schritt scheitert jeder Build** mit `denied: permission_denied`.

Repository → **Settings** → links **Actions** → **General** → ganz unten
**Workflow permissions** → **Read and write permissions** → **Save**

---

## Schritt 4 — Build starten (1–3 Min)

Der Upload aus Schritt 2 löst den Build bereits aus. Nachsehen:
Reiter **Actions** → oberster Eintrag.

Falls dort nichts steht oder Sie neu starten wollen:
**Actions** → links **Image bauen und veroeffentlichen** → rechts
**Run workflow** → **Run workflow**.

Grüner Haken = fertig. In der Zusammenfassung des Laufs steht die Zeile, die
Sie gleich brauchen:

```
ghcr.io/networxnet/flugspur:latest
```

### Wenn der Build rot wird

| Meldung | Ursache | Abhilfe |
|---|---|---|
| `denied: permission_denied` | Schritt 3 vergessen | Schritt 3 nachholen, Build erneut starten |
| `invalid reference format` | Großbuchstaben im Namen | sollte der Workflow abfangen; melden Sie mir die Zeile |
| kein Lauf sichtbar | `.github` fehlt im Upload | siehe Hinweis in Schritt 2 |

---

## Schritt 5 — Paket öffentlich stellen (2 Min)

**Das ist die Stelle, an der es am häufigsten klemmt.** Der Build ist grün,
das Image liegt bereit — aber GHCR stellt neue Pakete **privat** aus.
Portainer scheitert dann beim Laden mit `unauthorized` oder
`manifest unknown`, ohne dass erkennbar wäre, warum.

GitHub → Ihr Profilbild → **Your profile** → Reiter **Packages** →
`flugspur` → rechts **Package settings** → ganz unten **Danger Zone** →
**Change visibility** → **Public** → Namen zur Bestätigung eintippen.

---

## Schritt 6 — Ordner auf dem NAS anlegen (2 Min)

File Station → in der Freigabe `Container`:

```
Container/flugspur/data/
```

Nur `data` — die Python-Dateien werden **nicht** mehr gebraucht, sie stecken
jetzt im Image.

---

## Schritt 7 — Pfadtest (3 Min)

Portainer → **Stacks** → **Add stack** → Name `flugspur-pfadtest` →
**Web editor** → Inhalt von `docker-compose.pfadtest.yml` einfügen.

Unten bei **Environment variables** → **Add an environment variable**:

| Name | Value |
|---|---|
| `FS_DATA_PFAD` | `/share/CACHEDEV1_DATA/Container/flugspur/data` |

**Deploy the stack**, dann **Containers** → Logs von `flugspur-pfadtest-uid1000`
ansehen.

Entscheidend ist diese Zeile:

```
 Schreibtest /data als uid 1000:
   OK -- geschlossenes Image kann schreiben
```

Steht dort **FEHLGESCHLAGEN**, gehört der Ordner einem anderen Benutzer. Zwei
Auswege, beide in Ordnung:

- **A:** In `docker-compose.image.yml` bei allen drei Diensten `user: "0:0"`
  ergänzen — der Container läuft dann als root.
- **B:** In File Station Schreibrecht für alle auf `data` setzen.

Prüfen Sie im selben Log auch, ob **Port 14580** erreichbar ist. Ist er
blockiert, läuft ADS-B zwar, das OGN-Netz aber bleibt stumm — und die
Segelflieger und Ultraleichten fehlen in der Auswertung.

Danach Stack `flugspur-pfadtest` wieder **löschen**.

---

## Schritt 8 — Den richtigen Stack ausrollen (5 Min)

Portainer → **Stacks** → **Add stack** → Name `flugspur` →
**Web editor** → Inhalt von `docker-compose.image.yml` einfügen.

Bei **Environment variables** zwei Einträge:

| Name | Value |
|---|---|
| `FS_IMAGE` | `ghcr.io/networxnet/flugspur:latest` |
| `FS_DATA_PFAD` | `/share/CACHEDEV1_DATA/Container/flugspur/data` |

**Deploy the stack.**

Nach ein bis zwei Minuten laufen drei Container, `flugspur-adsb` wird **healthy**.
In File Station erscheinen unter `data/` die ersten Dateien:

```
adsb_2026-10-07.ndjson
ogn_2026-10-07.ndjson
_heartbeat_adsb.txt
```

**Ab hier läuft die Erfassung.** Weiter mit `BEDIENUNG.md`.

---

## Später: Änderungen und Versionen

**Code ändern:** Datei im GitHub-Webeditor bearbeiten → Commit → Build läuft
automatisch → in Portainer **Stacks → flugspur → Update the stack** mit
Haken bei **Re-pull image**.

**Feste Version festhalten:** Repository → **Releases** → **Create a new
release** → Tag `v1.0` → Publish. Danach existiert
`ghcr.io/networxnet/flugspur:1.0`. Tragen Sie diesen Tag statt `latest` in
`FS_IMAGE` ein — dann ändert sich Ihr laufendes System nie unbeabsichtigt.
Für Zahlen, die Sie öffentlich vertreten, ist das der saubere Weg: Sie können
jederzeit belegen, welche Programmfassung welche Auswertung erzeugt hat.

**Umzug auf einen Raspberry Pi:** Dieselbe Compose-Datei, nur
`FS_DATA_PFAD` anpassen. Das Image enthält arm64, Docker holt die richtige
Variante von selbst.

**Weitergabe an andere Initiativen:** Es genügt der Imagename plus
`docker-compose.image.yml`. Für einen anderen Flugplatz sind lediglich
`EDLN_LAT` und `EDLN_LON` zu ändern — und in `app/summary.py` bzw.
`app/visualize.py` die Liste `ORTE` mit den dortigen Ortslagen.
