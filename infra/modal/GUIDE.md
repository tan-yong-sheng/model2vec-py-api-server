# Modal Deployment Guide (Simple)

This guide keeps the Modal deployment steps short and practical.

## 1) What You Get

- A single Modal deployment serving the FastAPI app.
- Default model: `minishlab/potion-multilingual-128M`.
- Volume-cached model weights to avoid repeated downloads.
- Optional auth and optional HF token support.

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

## 4) Optional Secrets (Recommended)

### Auth tokens (optional)
If set, requests must include `Authorization: Bearer <token>`.

```bash
modal secret create model2vec-auth \
  AUTHENTICATION_ALLOWED_TOKENS=token1,token2
```

### Hugging Face token (optional)
If set, downloads from HF are faster and less rate-limited. But it's not necessary because we have persisted volume of downloaded models.

```bash
modal secret create model2vec-hf \
  HF_TOKEN=hf_xxx
```

## 5) Download the Model to the Volume (One-Time)

```bash
# If using secrets, set these first
export AUTH_SECRET_NAME=model2vec-auth
export HF_SECRET_NAME=model2vec-hf

modal run infra/modal/modal_config.py::download_models
```

## 6) Deploy

```bash
# If using secrets, keep these set
export AUTH_SECRET_NAME=model2vec-auth
export HF_SECRET_NAME=model2vec-hf

modal deploy infra/modal/modal_config.py
```

## 7) Quick Tests

```bash
# Replace with your deployed URL
APP_URL="https://<your-app>.modal.run"

curl -sS "$APP_URL/meta"
curl -sS "$APP_URL/v1/models"

curl -sS "$APP_URL/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"potion-multilingual-128M","input":"hello world"}'
```

## 8) Notes

- Auth is **optional**: if no auth tokens are set, requests are allowed.
- HF token is **optional**: improves download speed and rate limits.
- Cold starts are expected on the first embeddings request after idle.
