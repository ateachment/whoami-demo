import os
import socket
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)
START = time.time()
request_count = 0  # Zähler pro Pod, zeigt "Stateless" sehr anschaulich


@app.get("/")
def info():
    global request_count
    request_count += 1
    return jsonify(
        hostname=socket.gethostname(),            # Pod-Name
        pod_ip=os.getenv("POD_IP", "unbekannt"),
        node=os.getenv("NODE_NAME", "unbekannt"),
        version=os.getenv("APP_VERSION", "dev"),  # Git-Commit
        uptime_seconds=int(time.time() - START),
        requests_served_by_this_pod=request_count,
        timestamp=datetime.now(timezone.utc).isoformat(),
        client_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/crash")
def crash():
    # Nur für die Demo: Prozess beendet sich, Kubernetes startet den Container neu
    os._exit(1)
    