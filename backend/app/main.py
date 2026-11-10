import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import processing, store
from .providers import MissingCredentials, ProviderError
from .reasoning import ReasoningError
from .reviews import ReviewError
from .routes import conversations, resources

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app):
    # Recover polling for jobs interrupted by a local process restart.
    for c in store.all_conversations():
        if c.status == "analysing":
            processing.launch(c.id)
        elif c.audio_path and c.status not in ["ready", "failed"]:
            conversations.launch(c.id)
    yield
    for task in conversations.tasks:
        task.cancel()
    for task in processing.tasks:
        task.cancel()


app = FastAPI(title="VoiceBridge AI", version="0.1.0", lifespan=lifespan)
app.include_router(conversations.router)
app.include_router(resources.router)


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = str(uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def error(request: Request, exc: ValueError):
    code = (
        404
        if isinstance(exc, store.NotFound)
        else 409
        if isinstance(exc, (store.Conflict, ReviewError))
        else 503
        if isinstance(exc, MissingCredentials)
        else 502
        if isinstance(exc, (ProviderError, ReasoningError))
        else 422
    )
    message = (
        "Validation failed. Check the field values."
        if isinstance(exc, ValidationError)
        else str(exc)
    )
    return JSONResponse(
        status_code=code,
        content={
            "detail": message,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
