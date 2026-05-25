from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse

from auth import get_current_user
from auth_routes import admin_user_router, auth_router
from database import init_db
from llm import get_recommendations
from models import RecipeRequest, RecipeResponse
from observability import Trace, list_traces, load_trace, render_observability_dashboard, render_trace_report, render_trace_ui
from request_context import build_request_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="RAG Recipe API",
    description="Recipe recommendations powered by ChromaDB + Llama 3.1 70B via UF NaviGator",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_user_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check for load balancers, local scripts, and the frontend."""
    return {"status": "ok", "model": "llama-3.1-70b-instruct", "rag": "chromadb"}


@app.get("/admin/traces")
async def admin_traces(limit: int = 25) -> dict[str, object]:
    """List recent RAG traces for admin debugging."""
    return {"traces": list_traces(limit=limit)}


@app.get("/admin/observability", response_class=HTMLResponse)
async def admin_observability(limit: int = 25) -> str:
    """Return a human-readable observability dashboard."""
    return render_observability_dashboard(limit=limit)


@app.get("/admin/traces/{request_id}")
async def admin_trace_detail(request_id: str) -> dict[str, object]:
    """Return the full step-by-step RAG trace for one request."""
    return load_trace(request_id)


@app.get("/admin/traces/{request_id}/ui", response_class=HTMLResponse)
async def admin_trace_ui(request_id: str) -> str:
    """Return a human-readable trace detail page."""
    return render_trace_ui(load_trace(request_id))


@app.get("/admin/traces/{request_id}/report", response_class=PlainTextResponse)
async def admin_trace_report(request_id: str) -> str:
    """Return a human-readable RAG trace report."""
    return render_trace_report(load_trace(request_id))


@app.post("/recommend", response_model=RecipeResponse)
async def recommend(
    request: RecipeRequest,
    response: Response,
    _current_user: dict = Depends(get_current_user),
) -> RecipeResponse:
    """
    Return recipe recommendations grounded in ChromaDB context.
    Requires a valid JWT Bearer token in the Authorization header.
    """
    trace = Trace(request)
    response.headers["X-Trace-Id"] = trace.request_id

    if not request.navigator_token or len(request.navigator_token.strip()) < 10:
        exc = HTTPException(status_code=400, detail="A valid NaviGator API token is required.")
        trace.record_error(exc)
        trace.save()
        raise exc

    if request.mode == "ingredients" and not request.ingredients:
        exc = HTTPException(status_code=400, detail="Select at least one ingredient.")
        trace.record_error(exc)
        trace.save()
        raise exc

    try:
        request_context = await build_request_context(request)
        trace.set("context", request_context)
        recipes, retrieved_count = await get_recommendations(request, trace=trace)
        api_response = RecipeResponse(recipes=recipes, mode=request.mode, retrieved_count=retrieved_count)
        trace.update(
            "final_response",
            {
                "mode": api_response.mode,
                "retrieved_count": api_response.retrieved_count,
                "recipe_titles": [recipe.title for recipe in api_response.recipes],
                "recipes": [recipe.model_dump() for recipe in api_response.recipes],
            },
        )
        trace.save()
        return api_response
    except HTTPException as exc:
        trace.record_error(exc)
        trace.save()
        raise
    except Exception as exc:
        trace.record_error(exc)
        trace.save()
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
