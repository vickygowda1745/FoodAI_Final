import json
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

MODEL = "minicpm-v4.6:q4_K_M"
BASE = "http://127.0.0.1:11434"
LOG = Path.home() / "FoodAI_Final" / "logs" / "keep_hot.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(message):
    stamp = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(stamp + " - " + message + "\n")

def ollama_online():
    try:
        with urllib.request.urlopen(BASE + "/api/version", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False

if not ollama_online():
    log("Ollama offline; starting Ollama")
    subprocess.run(
        ["/usr/bin/open", "-ga", "Ollama"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(15):
        time.sleep(2)
        if ollama_online():
            break

if not ollama_online():
    log("FAILED - Ollama did not start")
    raise SystemExit(1)

payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "user",
            "content": "Reply only READY"
        }
    ],
    "stream": False,
    "keep_alive": "24h",
    "options": {
        "num_ctx": 2048,
        "num_predict": 4,
        "temperature": 0
    }
}

data = json.dumps(payload).encode("utf-8")

req = urllib.request.Request(
    BASE + "/api/chat",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=180) as r:
        body = json.loads(r.read().decode("utf-8"))

    if body.get("done") is True:
        log("MiniCPM HOT - keep alive renewed for 24 hours")
    else:
        log("MiniCPM request completed but done flag missing")

except Exception as e:
    log("MiniCPM preload FAILED - " + str(e))
    raise
