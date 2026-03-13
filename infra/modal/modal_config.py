from __future__ import annotations

import os
from pathlib import Path

import modal


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (
                (value.startswith("\"") and value.endswith("\""))
                or (value.startswith("'") and value.endswith("'"))
            ):
                value = value[1:-1]
            os.environ.setdefault(key, value)
    except Exception as exc:
        print(f"Failed to load env file {path}: {exc}", flush=True)


_load_env_file(Path(__file__).with_name(".env.modal"))

APP_NAME = os.environ.get("MODAL_APP_NAME", "model2vec-embeddings")
MODEL_VOLUME_NAME = os.environ.get("MODEL_VOLUME_NAME", "embedding-models")
MODEL_VOLUME_PATH = "/app/models"
HF_CACHE_PATH = f"{MODEL_VOLUME_PATH}/hf"
AUTH_SECRET_NAME = os.environ.get("AUTH_SECRET_NAME", "").strip()
HF_SECRET_NAME = os.environ.get("HF_SECRET_NAME", "").strip()

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install_from_requirements("src/requirements.txt")
    .env(
        {
            "PYTHONPATH": "/app",
            "HF_HOME": HF_CACHE_PATH,
            "HUGGINGFACE_HUB_CACHE": HF_CACHE_PATH,
            "TRANSFORMERS_CACHE": HF_CACHE_PATH,
            "AUTH_SECRET_NAME": AUTH_SECRET_NAME,
            "HF_SECRET_NAME": HF_SECRET_NAME,
            "MODEL_PATH": os.environ.get("MODEL_PATH", MODEL_VOLUME_PATH),
            **{
                key: value
                for key in (
                    "HF_TOKEN",
                    "HUGGINGFACE_HUB_TOKEN",
                    "MODEL_NAME",
                    "ALIAS_MODEL_NAME",
                    "LAZY_LOAD_MODEL",
                )
                if (value := os.environ.get(key)) not in (None, "")
            },
        }
    )
    .add_local_dir("src", remote_path="/app/src")
)

model_volume = modal.Volume.from_name(
    MODEL_VOLUME_NAME, create_if_missing=True)


def _ensure_env_defaults() -> None:
    os.environ.setdefault("MODEL_PATH", MODEL_VOLUME_PATH)
    os.environ.setdefault(
        "MODEL_NAME", "minishlab/potion-multilingual-128M"
    )
    os.environ.setdefault(
        "ALIAS_MODEL_NAME", "potion-multilingual-128M"
    )
    os.environ.setdefault("LAZY_LOAD_MODEL", "false")


def _get_secrets() -> list[modal.Secret]:
    secrets: list[modal.Secret] = []
    if AUTH_SECRET_NAME:
        secrets.append(modal.Secret.from_name(AUTH_SECRET_NAME))
    if HF_SECRET_NAME:
        secrets.append(modal.Secret.from_name(HF_SECRET_NAME))
    return secrets


@app.function(
    image=image,
    volumes={MODEL_VOLUME_PATH: model_volume},
    cpu=1,
    memory=4096,
    timeout=900,
    secrets=_get_secrets(),
)
def download_models() -> None:
    """One-time model download to the persistent Modal volume."""

    _ensure_env_defaults()
    from model2vec import StaticModel

    model_name = os.environ["MODEL_NAME"]
    os.makedirs(HF_CACHE_PATH, exist_ok=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get(
        "HUGGINGFACE_HUB_TOKEN")
    StaticModel.from_pretrained(model_name, token=token)
    model_volume.commit()


@app.cls(
    image=image,
    volumes={MODEL_VOLUME_PATH: model_volume},
    cpu=1,
    memory=3072,
    scaledown_window=180,
    min_containers=0,
    max_containers=10,
    enable_memory_snapshot=True,
    secrets=_get_secrets(),
)
class Model2VecApp:
    @modal.enter(snap=True)
    def _warmup(self) -> None:
        _ensure_env_defaults()
        os.chdir("/app")

        from src.app import initialize_app_state_sync

        initialize_app_state_sync(start_idle_monitor=False)

    @modal.asgi_app()
    def fastapi_app(self):
        _ensure_env_defaults()
        os.chdir("/app")

        from src.app import app as fastapi_app

        return fastapi_app
