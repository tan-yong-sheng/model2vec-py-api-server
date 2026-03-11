# Reference: https://github.com/BerriAI/litellm/issues/1647

from logging import getLogger
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from src.config import Config, get_config, set_config
from src.errors import ErrorResponse
from src.middleware import (
    AuthMiddleware,
    ConcurrencyLimitMiddleware,
    MaxContentLengthMiddleware,
    TimeoutMiddleware,
)
from src.vectorizer import VectorInput
from src.meta import Meta
from src.app_state import AppState

# Load environment variables from .env file
load_dotenv()

logger = getLogger("uvicorn")

meta_config: Meta
config: Config
app_state: AppState


@asynccontextmanager
async def lifespan(app: FastAPI):
    global meta_config
    global config
    global app_state

    config = Config.from_env()
    set_config(config)
    model_path = "./models"
    app_state = await AppState.create(config, model_path)

    meta_config = Meta(model_path)
    app_state.start_idle_monitor()

    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    MaxContentLengthMiddleware,
    max_content_length=get_config().request_body_limit_bytes,
)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    ConcurrencyLimitMiddleware,
    concurrency_limit=get_config().concurrency_limit,
)
app.add_middleware(TimeoutMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    if exc.errors():
        error = exc.errors()[0]
        message = error.get("msg", "Invalid request")
        loc = error.get("loc", [])
        param = ".".join(str(part) for part in loc if part != "body") or None
    else:
        message = "Invalid request"
        param = None

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse.invalid_request(message, param=param).to_dict(),
    )


@app.get("/")
async def index():
    return {
        "service": "model2vec-api",
        "status": "ready" if await app_state.is_ready() else "starting",
        "endpoints": {
            "live": "/.well-known/live",
            "ready": "/.well-known/ready",
            "models": "/v1/models",
            "embeddings": "/v1/embeddings",
        },
    }


async def _set_live_response(response: Response) -> None:
    response.status_code = status.HTTP_200_OK


@app.get("/.well-known/live", response_class=Response)
async def live(response: Response):
    await _set_live_response(response)


@app.get("/.well_known/live", response_class=Response)
async def live_underscore(response: Response):
    await _set_live_response(response)


async def _ready_response(response: Response):
    if await app_state.is_ready():
        response.status_code = status.HTTP_200_OK
        return None
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse.server_error("Model not loaded").to_dict(),
    )


@app.get("/.well-known/ready", response_class=Response)
async def ready(response: Response):
    return await _ready_response(response)


@app.get("/.well_known/ready", response_class=Response)
async def ready_underscore(response: Response):
    return await _ready_response(response)


@app.get("/meta")
def meta(response: Response):
    cfg = get_config()
    return {
        "model_path": "",
        "model_name": cfg.model_name,
    }


def get_available_model():
    cfg = get_config()
    return cfg.model_name


def get_model_alias():
    return get_config().alias_model_name


@app.get("/v1/models")
@app.get("/models")
async def list_models(
    response: Response,
):
    try:
        model_display_name = get_available_model()
        model_alias = get_model_alias()

        models = [
            {
                "id": model_display_name,
                "object": "model",
                "created": 1700000000,
                "owned_by": "minishlab",
                "permission": [],
                "root": model_display_name,
                "parent": None,
            }
        ]

        # Add alias as a separate model if set
        if model_alias and model_alias != model_display_name:
            models.append(
                {
                    "id": model_alias,
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "minishlab",
                    "permission": [],
                    "root": model_alias,
                    "parent": model_display_name,
                }
            )

        return {"object": "list", "data": models}
    except Exception as e:
        logger.exception("Something went wrong while listing models.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.server_error("Internal server error").to_dict(),
        )


@app.post("/v1/embeddings")
@app.post("/embeddings")
async def embed(item: VectorInput, response: Response):
    try:
        # Validate model parameter
        available_model = get_available_model()
        model_alias = get_model_alias()

        # Accept either real model name or alias
        if item.model != available_model and item.model != model_alias:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse.invalid_request(
                    f"Model '{item.model}' not found. Available model: '{available_model}'",
                    param="model",
                ).to_dict(),
            )

        vectorizer = await app_state.get_vectorizer()
        vector = await vectorizer.vectorize(item.input, item.config)

        # Handle dimensions parameter (truncate if specified)
        if item.dimensions and item.dimensions > 0:
            vector = vector[:, : item.dimensions]

        # Convert to list for JSON serialization
        vector_list = vector.tolist()

        # Handle encoding format
        if item.encoding_format == "base64":
            import base64
            import numpy as np

            # Convert to base64 encoded string
            data = []
            for i, embedding in enumerate(vector_list):
                arr = np.array(embedding, dtype=np.float32)
                encoded = base64.b64encode(arr.tobytes()).decode("utf-8")
                data.append({
                    "object": "embedding",
                    "index": i,
                    "embedding": encoded,
                })
        else:
            # Default float format
            data = []
            for i, embedding in enumerate(vector_list):
                data.append({
                    "object": "embedding",
                    "index": i,
                    "embedding": embedding,
                })

        # Calculate token usage (approximate)
        if isinstance(item.input, list):
            input_texts = list(item.input)
        else:
            input_texts = [item.input]

        total_tokens = sum(len(text.split()) for text in input_texts)

        return {
            "object": "list",
            "data": data,
            "model": item.model,
            "usage": {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens,
            },
        }
    except TimeoutError:
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content=ErrorResponse.server_error("Request timed out").to_dict(),
        )
    except Exception as e:
        logger.exception("Something went wrong while vectorizing data.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.server_error("Internal server error").to_dict(),
        )
