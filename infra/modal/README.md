# Modal Deployment (Condensed Docs)

This directory now contains **two docs**:

1. `GUIDE.md` — The simple deployment guide
2. `README.md` — This quick entry point

If you are implementing or reviewing the deployment, **start with `GUIDE.md`**.

Key implementation file:
- `infra/modal/modal_config.py`

## Quick Commands

- Download model to the Modal volume (one-time):
  `modal run infra/modal/modal_config.py::download_models`
- Deploy the API:
  `modal deploy infra/modal/modal_config.py`

---

## Why It Changed

You requested fewer docs and a plan that is **cost-aware (<$30/month credit)** and aligned to:
- Default model: `minishlab/potion-multilingual-128M`
- Lower idle spend
- Better cold start/cost trade-offs

---

## Quick Start

- Read: `PLAN.md`
- Confirm: whether you want **single service** or **split metadata vs embeddings**
- Proceed with Phase 1 in the plan
