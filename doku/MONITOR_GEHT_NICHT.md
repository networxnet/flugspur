# Der Monitor zeigt nichts — Checkliste

Der Reihe nach durchgehen. Nach jedem Punkt noch einmal probieren.
Die Aufzeichnung läuft während all dieser Schritte ungestört weiter —
der Monitor liest nur mit.

## 1. Die Adresse

```
http://192.168.x.x:8099
```

Drei typische Fehler:

- **`https://` statt `http://`.** Browser ergänzen das heute oft von
  selbst. Tippen Sie `http://` ausdrücklich mit. Gegenprobe im privaten
  Fenster, dort greift die gemerkte Weiterleitung nicht.
- **`localhost` oder `127.0.0.1`.** Das zeigt auf Ihren eigenen PC, nicht
  aufs NAS. Nehmen Sie dieselbe Adresse, unter der Sie Portainer aufrufen.
- **Port vergessen.** Ohne `:8099` landen Sie auf der QNAP-Oberfläche.

## 2. Gibt es den Container überhaupt?

Portainer → **Containers**. Suchen Sie `flugspur-monitor`.

- **Nicht vorhanden** → Die neue Compose-Datei wurde noch nicht
  eingespielt. Entweder Stack `flugspur` aktualisieren oder — einfacher —
  den eigenen Stack aus `docker-compose.monitor.yml` anlegen (Punkt 6).
- **Vorhanden, aber rot / „Restarting"** → weiter bei Punkt 3.
- **Grün** → weiter bei Punkt 4.

## 3. Das Log lesen

Portainer → Containers → `flugspur-monitor` → **Logs**.

Im Normalfall steht dort:

```
Flugspur-Monitor laeuft auf Port 8099
Im Browser oeffnen:  http://<Adresse-des-NAS>:8099
Datenverzeichnis: /data | Platz: EDLN (Moenchengladbach)
Gefundene Dateien in /data: 4
   _heartbeat_adsb.txt
   _heartbeat_ogn.txt
   adsb_2026-10-08.ndjson
   ogn_2026-10-08.ndjson
Bereit. Jetzt im Browser oeffnen (http://, nicht https://).
```

Andernfalls:

| Meldung | Bedeutung |
|---|---|
| `can't open file '/app/monitor.py'` | `monitor.py` liegt nicht im `app`-Ordner — hochladen |
| `Profil nicht gefunden … Verfuegbar: (keine)` | Der Ordner `plaetze/` fehlt in `app/` |
| `Gefundene Dateien in /data: 0` | Monitor zeigt auf ein anderes Verzeichnis als die Logger |
| `address already in use` | Port 8099 ist belegt — Punkt 5 |

## 4. Antwortet der Server?

Portainer → Containers → `flugspur-monitor` → **Console** → `/bin/sh` →
**Connect**, dann einzeln eingeben:

```sh
python3 -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8099/healthz').read())"
```

- Kommt `b'ok'`, läuft der Server einwandfrei. Das Problem liegt dann
  zwischen Ihrem PC und dem NAS: Portfreigabe, Firewall, falsche Adresse.
- Kommt ein Fehler, startet der Server nicht — zurück zu Punkt 3.

## 5. Port belegt oder blockiert

In `docker-compose.monitor.yml` nur die **linke** Zahl ändern:

```yaml
    ports:
      - "8111:8099"
```

Danach `http://<NAS>:8111` aufrufen. Die rechte Zahl bleibt immer 8099 —
das ist der Port *innerhalb* des Containers.

Prüfen Sie außerdem in der QNAP-Systemsteuerung unter **Sicherheit**, ob
eine Firewallregel ausgehende Ports einschränkt.

## 6. Der sichere Weg: eigener Stack

Wenn unklar ist, woran es liegt, lassen Sie den laufenden Stack in Ruhe
und legen den Monitor getrennt an:

Portainer → **Stacks** → **Add stack** → Name `flugspur-monitor` →
**Web editor** → Inhalt von `docker-compose.monitor.yml` einfügen →
**Deploy the stack**.

Dieser Stack bindet `/app` und `/data` **nur lesend** ein. Er kann die
Aufzeichnung nicht beschädigen und lässt sich beliebig oft löschen und
neu anlegen.

## 7. Ganz ohne Browser

Wenn Sie nur sehen wollen, ob Daten hereinkommen, genügt die Konsole
eines bereits laufenden Containers:

```sh
docker exec -it flugspur-summary python3 /app/monitor.py --konsole
```

Textausgabe, aktualisiert sich alle 10 Sekunden, Abbruch mit Strg+C.
Oder noch einfacher, einzeln eingeben:

```sh
cat /data/_heartbeat_adsb.txt
```
