# Geschlossenes Image oder eingehängter Ordner?

Sie haben eingewandt, ein geschlossener Stack sei portabler und löse die
Bindung ans QNAP. Nachgeprüft — das Ergebnis ist geteilt.

---

## Was gegen `build:` in Portainer spricht (belegt)

Der naheliegende Weg „Dockerfile dazulegen und Portainer bauen lassen"
funktioniert nicht zuverlässig:

- **Web-Editor:** Beim Einfügen der YAML lädt Portainer *nur* diese Datei
  hoch — nicht den Dockerfile, nicht den Quellcode. Der Build scheitert mit
  `unable to prepare context: path … not found`.
- **Git-Repository:** Portainer dokumentiert selbst, dass das Bauen von
  Images aus Git-Stacks „not fully implemented" ist.
- **Agent-Umgebungen:** Build-Direktiven sind dort generell nicht
  unterstützt.

Die offizielle Empfehlung von Portainer lautet: **Image extern bauen, per
`image:` deployen.** Ein `build:` im Compose ist also in beiden Fällen der
falsche Weg — unabhängig davon, wie wir uns sonst entscheiden.

---

## Die beiden tragfähigen Wege

### Weg A — Eingehängter Ordner (`docker-compose.qnap.yml`)

Offizielles `python:3.12-slim`, die fünf `.py`-Dateien liegen auf dem NAS.

**Dafür:** Heute in 15 Minuten produktiv, rein grafisch, kein Konto nötig.
Änderungen an einem Skript = Datei ersetzen, Container neu starten.
Debugging ist trivial, weil man den Code sieht.

**Dagegen:** Keine Versionierung. Wer die Datei auf dem NAS ändert, ändert
das laufende System. Nicht an Dritte verteilbar.

**Zur Portabilität:** Der häufig vermutete Nachteil stimmt so *nicht*. Es
gibt genau **eine** QNAP-spezifische Zeile — den Pfad. Umzug auf einen Pi =
Ordner kopieren, Pfad ändern. `python:3.12-slim` ist multi-arch und zieht auf
dem Pi automatisch arm64. Der Umzug dauert fünf Minuten.

### Weg B — Geschlossenes Image aus der Registry (`docker-compose.yml`)

Der Code ist fest ins Image gebacken, auf dem Host liegen nur noch Daten.

**Dafür:**
- Unveränderlich und versioniert (`:1.0`, `:1.1`) — nachvollziehbar, welche
  Fassung welche Zahlen erzeugt hat. Für eine Bürgerinitiative, die Daten
  öffentlich vertritt, ist das ein ernstes Argument.
- Rollback durch Tag-Wechsel.
- **An andere Initiativen verteilbar.** AIRPEACE hat acht BIs. Für die ist
  eine Zeile `image: ghcr.io/…/flugspur:1.0` ungleich einfacher als fünf
  Python-Dateien mit Einbauanleitung. Das halte ich für das stärkste
  Argument — stärker als die Portabilität selbst.
- In der Compose-Datei steht **kein einziger fester Pfad**; der Datenpfad
  kommt als Portainer-Variable. Die Datei ist damit buchstäblich identisch
  auf QNAP und Pi.

**Dagegen:** Braucht einen GitHub-Account und einen einmaligen Aufbau.
Jede Codeänderung erfordert einen Rebuild, bevor sie wirkt.

**Zeitbedarf, nachgerechnet:**

| Schritt | Dauer |
|---|---|
| GitHub-Konto, falls noch keins | 5 Min |
| Repository anlegen, Dateien per Drag & Drop hochladen | 10 Min |
| Actions-Schreibrechte aktivieren | 2 Min |
| Build-Durchlauf (automatisch) | 1–3 Min |
| Paket auf "public" stellen | 2 Min |
| Stack in Portainer deployen | 5 Min |
| **Summe** | **rund 30 Minuten** |

Der Build ist deshalb so kurz, weil das Image nichts kompiliert: Es kopiert
fünf Textdateien auf ein fertiges Python-Image. Das `Dockerfile` kommt
bewusst **ohne einen einzigen `RUN`-Befehl** aus — dadurch muss für arm64
nichts emuliert werden (kein QEMU), und beide Architekturen entstehen in
Sekunden.

**Das Build-Problem ist gelöst:** Sie brauchen *keinen* Build-Rechner.
`.github/workflows/build.yml` lässt GitHub Actions das Image kostenlos für
**amd64 und arm64** bauen und nach ghcr.io laden. Alles im Browser.

---

## Empfehlung: beides, aber nacheinander

Der Streitpunkt ist kein Entweder-oder, sondern eine Reihenfolge.

**Jetzt — Weg A.** Der einzige Fehler, den Sie bei diesem Projekt machen
können, ist, keine Daten zu haben. Jeder Tag ohne Mitschnitt ist unwiederbringlich:
DFS-Radardaten gibt es nachträglich nur kostenpflichtig und nur binnen rund
30 Tagen. Die Erfassung heute zu starten ist mehr wert als die sauberere
Architektur nächste Woche.

**Danach — Weg B.** Sobald Daten fließen und die Skripte sich im echten
Betrieb bewährt haben, bauen wir in Ruhe das Image. Dann ist auch klar, was
überhaupt hineingehört — erfahrungsgemäß ändert sich in der ersten Woche
noch etwas.

**Der Umstieg ist schmerzlos:** Stack A löschen, Stack B mit demselben
`FS_DATA_PFAD` deployen. Die Daten liegen in beiden Fällen im selben
Ordner auf dem NAS und bleiben vollständig erhalten. Kein Export, kein
Import, keine Lücke im Mitschnitt.

Wenn Sie den Zwischenschritt überspringen wollen, ist das ebenfalls gut
vertretbar — dann richten wir direkt Weg B ein, und die Erfassung startet
rund 30 Minuten später statt sofort.

---

## Dateien dafür

| Datei | Zweck |
|---|---|
| `docker-compose.qnap.yml` | Weg A, Bind-Mount, feste QNAP-Pfade |
| `docker-compose.yml` | Weg B, geschlossenes Image, **ohne** feste Pfade |
| `docker-compose.pfadtest.yml` | Vorabtest für beide Wege |
| `Dockerfile` | Bauvorschrift, unprivilegiert (uid 1000) |
| `.github/workflows/build.yml` | automatischer Multi-Arch-Build nach ghcr.io |

---

## Ein Fallstrick, den ich zuerst übersehen hatte

Das Image läuft aus Sicherheitsgründen als **Benutzer 1000**, nicht als root.
Ein per File Station angelegter QNAP-Ordner gehört aber unter Umständen einem
anderen Benutzer — dann kann der Container nicht schreiben.

Mein erster Pfadtest lief als root und hätte „Schreiben möglich" gemeldet,
während der echte Container scheitert. Das war eine Falle in meiner eigenen
Anleitung. Der Pfadtest prüft jetzt **beide** Fälle getrennt und nennt im
Fehlerfall zwei konkrete Auswege (`user: "0:0"` ergänzen oder Ordnerrechte
setzen).

### Der zweite Fallstrick: GHCR-Pakete sind standardmäßig privat

Nach dem ersten erfolgreichen Build liegt das Image in der GitHub Container
Registry — aber **nicht öffentlich**. Portainer scheitert dann beim Pull mit
`unauthorized` oder `manifest unknown`, obwohl der Build grün war.

Abhilfe, einmalig: GitHub → Ihr Profil → **Packages** → `flugspur` →
**Package settings** → ganz unten **Change visibility** → *Public*.

Ohne diesen Schritt müssten Sie in Portainer Registry-Zugangsdaten
hinterlegen. Für ein Werkzeug, das ohnehin an andere Initiativen gehen soll,
ist "public" der richtige Weg.

### Und noch einer: Port 14580

Der Pfadtest prüft außerdem, ob **Port 14580** zum OGN-Netz offen ist. Manche
NAS-Firewalls blockieren ausgehende Nicht-Standardports — das würde sonst
erst auffallen, wenn die OGN-Datei nach Tagen leer bleibt.
