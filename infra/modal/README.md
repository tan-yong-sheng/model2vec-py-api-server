# Modal Deployment

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
