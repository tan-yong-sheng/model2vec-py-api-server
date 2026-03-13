# Modal Deployment Guide (Simple)

This guide keeps the Modal deployment steps short and practical.

## 1) What You Get

- A single Modal deployment serving the FastAPI app.
- Default model: `minishlab/potion-multilingual-128M`.
- Volume-cached model weights to avoid repeated downloads.
- Optional auth and optional HF token support.
- Memory snapshots enabled to reduce cold-start time after initial warmup.

## 2) Files

- `infra/modal/modal_config.py` — Modal entrypoint
- `infra/modal/README.md` — quick commands
- `src/*` — FastAPI app (already in place)

## 3) One-Time Setup

```bash
# Install Modal CLI (if not installed)
# https://modal.com/docs/guide

# Create a volume for model caching
modal volume create embedding-models
```

## 4) Local Env (Recommended)

Create or edit `infra/modal/.env.modal` with your local settings. Example keys:

- `MODAL_APP_NAME`
- `MODEL_VOLUME_NAME`
- `MODEL_PATH` (defaults to `/app/models`)
- `MODEL_NAME`, `ALIAS_MODEL_NAME`
- `LAZY_LOAD_MODEL` (set to `false` to preload during snapshot)

## 5) Optional Secrets (Auth Only)

If set, requests must include `Authorization: Bearer <token>`.

```bash
modal secret create model2vec-auth \
  AUTHENTICATION_ALLOWED_TOKENS=token1,token2
```

## 6) Download the Model to the Volume (One-Time)

```bash
# If using auth secrets, set this (or use .env.modal)
export AUTH_SECRET_NAME=model2vec-auth

modal run infra/modal/modal_config.py::download_models
```

## 7) Deploy

```bash
# If using auth secrets, keep this set (or use .env.modal)
export AUTH_SECRET_NAME=model2vec-auth

modal deploy infra/modal/modal_config.py
```

## 8) Build the Memory Snapshot (Recommended)

After deploy, hit the app once to build the snapshot. This makes subsequent cold
starts faster. Replace with your deployed URL:

```bash
APP_URL="https://<your-app>.modal.run"
curl -sS "$APP_URL/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"potion-multilingual-128M","input":"hello world"}'
```

## 9) Quick Tests

```bash
# Replace with your deployed URL
APP_URL="https://<your-app>.modal.run"

curl -sS "$APP_URL/meta"
curl -sS "$APP_URL/v1/models"

curl -sS "$APP_URL/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"potion-multilingual-128M","input":"hello world"}'
```

## 10) Notes

- Auth is **optional**: if no auth tokens are set, requests are allowed.
- HF token is **optional**: it is only used by the one-time `download_models` step to speed up or allow access to gated models. It is not required for serving once the model is cached in the volume.
- Cold starts are expected on the first embeddings request after idle.
  With memory snapshots, later cold starts are typically faster.
