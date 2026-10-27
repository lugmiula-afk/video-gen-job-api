"""One worker = one GPU (pin with NVIDIA_VISIBLE_DEVICES). Mock mode if COMFY_URL is empty."""
import json, os, time, redis, requests

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
COMFY = os.environ.get("COMFY_URL", "")
MAX_ATTEMPTS = 3

def run_comfy(payload):
    # Load a versioned workflow JSON, inject prompt/seed, POST /prompt, poll /history/{id}.
    wf = json.load(open("/workflows/t2v.json"))   # mount your exported ComfyUI API workflow
    resp = requests.post(f"{COMFY}/prompt", json={"prompt": wf}, timeout=30)
    resp.raise_for_status()
    pid = resp.json()["prompt_id"]
    while True:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=30).json()
        if pid in h:
            return h[pid]
        time.sleep(2)

def process(jid):
    key = f"job:{jid}"
    if r.hget(key, "status") == "cancelled":
        return
    payload = json.loads(r.hget(key, "payload"))
    r.hset(key, "status", "running")
    r.hincrby(key, "attempts", 1)
    try:
        if COMFY:
            run_comfy(payload)
        else:
            time.sleep(3)                         # mock inference
        path = f"/artifacts/{jid}.txt"
        open(path, "w").write(f"mock artifact for: {payload['prompt']}\n")
        r.hset(key, mapping={"status": "succeeded", "artifact": path})
    except Exception as e:
        attempts = int(r.hget(key, "attempts"))
        if attempts < MAX_ATTEMPTS:
            r.hset(key, "status", "queued")
            time.sleep(2 ** attempts)             # exponential backoff
            r.lpush("queue", jid)
        else:
            r.hset(key, mapping={"status": "failed", "error": str(e)})
            r.lpush("dlq", jid)

while True:
    item = r.brpop("queue", timeout=5)
    if item:
        process(item[1])
