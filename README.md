# video-gen-job-api (PoC)
Minimal reference for a GPU job platform: FastAPI -> Redis queue -> one-GPU workers -> artifacts.
Mock mode needs no GPU. Set COMFY_URL and mount an exported ComfyUI workflow for real inference.

    docker compose up --build
    curl -X POST localhost:8000/v1/jobs -H 'x-api-key: change-me' -H 'content-type: application/json' \
         -d '{"prompt":"a fox running","idempotency_key":"demo-1"}'
    curl localhost:8000/v1/jobs/<id> -H 'x-api-key: change-me'

Implemented: idempotency, cancel, retry with exponential backoff, dead-letter queue.
Not implemented (see proposal): OIDC/RBAC, VRAM-aware scheduler, S3 + signed URLs, metrics (DCGM/Prometheus).
