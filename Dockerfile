# Geschlossenes Image: Code fest eingebacken, keine externen Abhaengigkeiten.
#
# Bewusst OHNE jeden RUN-Befehl. Dadurch muss beim Multi-Arch-Build nichts
# emuliert werden (kein QEMU) -- der Build fuer amd64 UND arm64 dauert
# dann nur wenige Sekunden statt mehrerer Minuten.
#
# Statt per useradd einen Benutzer anzulegen (was ein RUN erfordern wuerde),
# laeuft der Prozess unter einer nackten numerischen UID. Linux erlaubt das;
# ein Eintrag in /etc/passwd ist nicht noetig.
FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="Flugspur"
LABEL org.opencontainers.image.description="Mitschnitt und Auswertung von Flugbewegungen (ADS-B/MLAT und OGN/FLARM) rund um einen Flugplatz. Reine Python-Standardbibliothek, platzunabhaengig."
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Berlin \
    HOME=/tmp \
    EDLN_DATA_DIR=/data

# --chown setzt die Rechte beim Kopieren -- kein RUN noetig
COPY --chown=1000:1000 app/ /app/

WORKDIR /app
USER 1000:1000

HEALTHCHECK --interval=60s --timeout=10s --start-period=90s --retries=3 \
  CMD python3 -c "import time,sys,os;p=os.environ.get('TRACKER_HEARTBEAT','/data/_heartbeat_adsb.txt');t=int(open(p).readline());sys.exit(0 if time.time()-t<180 else 1)"

CMD ["python3", "/app/adsb_logger.py"]
