# Dockerfile: Bauanleitung für das Image (wird in der GitHub-Pipeline mit "docker build" ausgeführt)

# Basis-Image: Linux mit Python 3.12. "slim" = abgespeckt, daher kleiner und schneller zu laden.
# Hier liegt die "Bin/Library"-Schicht aus dem Bild: Betriebssystem-Dateien und Python, aber kein eigener Kernel.
FROM python:3.12-slim

# Arbeitsverzeichnis im Image. Alle folgenden Befehle laufen hier. Existiert es nicht, wird es angelegt.
WORKDIR /app

# Erst nur die Abhängigkeitsliste kopieren, dann installieren.
# Grund: Docker speichert jeden Schritt als Schicht (Layer) zwischen. Ändert sich nur app.py,
# bleibt diese Schicht im Cache, und der Build geht deutlich schneller.
COPY requirements.txt .

# Abhängigkeiten (Flask, Gunicorn) werden beim BAUEN installiert, nicht beim Start.
# --no-cache-dir: Der pip-Cache bleibt nicht im Image, das spart Platz.
RUN pip install --no-cache-dir -r requirements.txt

# Jetzt erst den eigenen Code kopieren. Er ändert sich am häufigsten, deshalb steht er weit unten.
COPY app.py .

# Build-Argument: Wird in der Pipeline übergeben (build-args: APP_VERSION=<Commit-Hash>).
# Standardwert "dev" gilt bei einem lokalen Build ohne Argument.
ARG APP_VERSION=dev

# Macht daraus eine Umgebungsvariable im laufenden Container.
# app.py liest sie aus und zeigt sie im Feld "version" an. So ist jedes Image seinem Commit zuordenbar.
ENV APP_VERSION=${APP_VERSION}

# Sicherheit: eigenen Benutzer ohne Admin-Rechte anlegen (-r = Systembenutzer) ...
RUN useradd -r appuser

# ... und alle folgenden Schritte sowie den Container selbst als dieser Benutzer ausführen.
# Container sollen nicht als root laufen. Deshalb auch Port 8080 statt 80 (Ports unter 1024 sind privilegiert).
USER appuser

# Dokumentation: Der Dienst lauscht auf Port 8080. Veröffentlicht wird der Port dadurch NICHT,
# das übernehmen Kubernetes (containerPort) und der Service (targetPort).
EXPOSE 8080

# Startbefehl des Containers. Gunicorn ist der produktive Webserver, "app:app" = Datei app.py, Variable app (Flask).
# Variante mit 2 Prozessen: zwei Worker, jeder mit eigenem Zähler (wäre verwirrend für die Demo).
# CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "app:app"]

# Aktuell: 1 Worker-Prozess mit 4 Threads.
#   -b 0.0.0.0:8080 -> auf allen Netzwerkschnittstellen lauschen (sonst von außen nicht erreichbar)
#   -w 1            -> ein Prozess, daher ein Zähler pro Pod
#   --threads 4     -> bis zu 4 Anfragen gleichzeitig, alle teilen sich den Speicher des Prozesses
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "--threads", "4", "app:app"]