import base64
import os
import socket
import threading
import time
from datetime import datetime, timezone

import redis
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

START = time.time()
request_count = 0                 # Zähler im Speicher dieses Prozesses (geht beim Neustart verloren)
count_lock = threading.Lock()     # schützt den Zähler, weil mehrere Threads gleichzeitig zugreifen

# Verbindung zu Redis. "redis" ist der Name des Kubernetes-Service (cluster-internes DNS).
# Kurze Timeouts: Ist Redis weg, soll die App nicht hängen, sondern sofort ohne Zähler antworten.
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def shared_counter():
    """Gemeinsamer Zähler in Redis. Liefert None, wenn Redis nicht erreichbar ist."""
    try:
        return r.incr("requests_total")   # atomar: auch bei vielen Pods gibt es keine doppelten Werte
    except redis.RedisError:
        return None


@app.get("/")
def info():
    global request_count
    with count_lock:
        request_count += 1
        local_count = request_count

    return jsonify(
        hostname=socket.gethostname(),            # Pod-Name
        pod_ip=os.getenv("POD_IP", "unbekannt"),
        node=os.getenv("NODE_NAME", "unbekannt"),
        version=os.getenv("APP_VERSION", "dev"),  # Git-Commit
        process_uptime_seconds=int(time.time() - START),
        process_requests_served=local_count,      # lokal: springt zwischen Pods, Reset bei Neustart
        requests_total=shared_counter(),          # gemeinsam: steigt über alle Pods, null = Redis nicht erreichbar
        timestamp=datetime.now(timezone.utc).isoformat(),
        client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
    )


@app.get("/health")
def health():
    # Bewusst ohne Redis-Prüfung: Fällt Redis aus, sollen die Web-Pods im Loadbalancer bleiben.
    return {"status": "ok"}


@app.get("/crash")
def crash():
    # Nur für die Demo: Prozess beendet sich, Kubernetes startet den Container neu
    os._exit(1)


# 1x1 Pixel, transparentes GIF
PIXEL = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

@app.get("/ping.gif")
def ping():
    # Kein Cache, sonst zeigt der Browser einen alten Zustand
    return Response(PIXEL, mimetype="image/gif", headers={"Cache-Control": "no-store"})