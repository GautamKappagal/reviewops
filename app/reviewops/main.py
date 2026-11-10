"""FastAPI entry point:  uvicorn reviewops.main:app"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .config import get_settings
from .llm import get_llm
from .logging_setup import log_event, setup_logging
from .reviewer import run_review
from .schemas import ReviewRequest
from .store import ReviewStore
from .ui import render_index

settings = get_settings()
llm = get_llm(settings)
store = ReviewStore(settings.max_history)
logger = setup_logging()

app = FastAPI(title="ReviewOps", version=settings.app_version)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/version")
def version():
    return {
        "app_version": settings.app_version,
        "prompt_version": settings.prompt_version,
        "model": llm.name,
    }


@app.post("/review")
def review(req: ReviewRequest):
    result = run_review(req.model_dump(), llm, settings)
    store.add(result)
    log_event(
        logger, "review_completed",
        review_id=result["review_id"], repo=result["repo"], pr_number=result["pr_number"],
        verdict=result["verdict"], comment_count=len(result["comments"]),
        latency_ms=result["latency_ms"], model=result["model"],
        prompt_version=result["prompt_version"], app_version=result["app_version"],
    )
    return result


@app.get("/reviews")
def reviews(limit: int = 20):
    return store.recent(limit)


@app.get("/", response_class=HTMLResponse)
def index():
    return render_index(settings, store.recent(20))
