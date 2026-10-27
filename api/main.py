import os, time, uuid
import redis
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
API_KEY = os.environ.get("API_KEY", "change-me")
app = FastAPI(title="Video generation job API (PoC)")

class JobIn(BaseModel):
    prompt: str
    model: str = "wan2.2-ti2v-5b"
    seed: int = 42
    duration_s: int = 5
    resolution: str = "720p"
    idempotency_key: str | None = None

def auth(key):
    if key != API_KEY:
        raise HTTPException(401, "bad api key")

@app.post("/v1/jobs", status_code=202)
def create(job: JobIn, x_api_key: str = Header(None)):
    auth(x_api_key)
    if job.idempotency_key:
        existing = r.get(f"idem:{job.idempotency_key}")
        if existing:
            return {"id": existing, "status": r.hget(f"job:{existing}", "status")}
    jid = uuid.uuid4().hex
    r.hset(f"job:{jid}", mapping={"status": "queued", "payload": job.model_dump_json(),
                                   "created": time.time(), "attempts": 0})
    if job.idempotency_key:
        r.set(f"idem:{job.idempotency_key}", jid, ex=86400)
    r.lpush("queue", jid)
    return {"id": jid, "status": "queued"}

@app.get("/v1/jobs/{jid}")
def get(jid: str, x_api_key: str = Header(None)):
    auth(x_api_key)
    j = r.hgetall(f"job:{jid}")
    if not j:
        raise HTTPException(404)
    return {"id": jid, "status": j["status"], "artifact": j.get("artifact"), "error": j.get("error")}

@app.post("/v1/jobs/{jid}/cancel")
def cancel(jid: str, x_api_key: str = Header(None)):
    auth(x_api_key)
    if r.hget(f"job:{jid}", "status") in ("queued", "running"):
        r.hset(f"job:{jid}", "status", "cancelled")
    return {"id": jid, "status": r.hget(f"job:{jid}", "status")}
