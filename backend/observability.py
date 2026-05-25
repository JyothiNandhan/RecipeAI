from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from fastapi import HTTPException

BASE_DIR = Path(__file__).resolve().parent
TRACE_DIR = BASE_DIR / "logs" / "traces"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_request_payload(request: Any) -> dict[str, Any]:
    payload = request.model_dump() if hasattr(request, "model_dump") else dict(request)
    token = payload.pop("navigator_token", "")
    payload["navigator_token"] = {
        "present": bool(token),
        "length": len(token),
    }
    return payload


class Trace:
    def __init__(self, request: Any) -> None:
        self.request_id = uuid.uuid4().hex[:12]
        self.data: dict[str, Any] = {
            "request_id": self.request_id,
            "started_at": utc_now(),
            "finished_at": None,
            "request": safe_request_payload(request),
            "context": {},
            "vector_db": {},
            "augmentation": {},
            "llm": {},
            "post_processing": {},
            "final_response": {},
            "error": None,
        }

    def set(self, section: str, value: Any) -> None:
        self.data[section] = value

    def update(self, section: str, values: dict[str, Any]) -> None:
        current = self.data.get(section)
        if not isinstance(current, dict):
            current = {}
        current.update(values)
        self.data[section] = current

    def record_error(self, exc: Exception) -> None:
        detail = getattr(exc, "detail", str(exc))
        self.data["error"] = {
            "type": exc.__class__.__name__,
            "status_code": getattr(exc, "status_code", None),
            "detail": detail,
        }

    def save(self) -> None:
        self.data["finished_at"] = utc_now()
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        path = TRACE_DIR / f"{self.request_id}.json"
        path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_traces(limit: int = 25) -> list[dict[str, Any]]:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(TRACE_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    traces: list[dict[str, Any]] = []
    for path in paths[:limit]:
        try:
            trace = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        traces.append(
            {
                "request_id": trace.get("request_id"),
                "started_at": trace.get("started_at"),
                "finished_at": trace.get("finished_at"),
                "mode": trace.get("request", {}).get("mode"),
                "input": {
                    "ingredients": trace.get("request", {}).get("ingredients"),
                    "dietary_goal": trace.get("request", {}).get("dietary_goal"),
                    "max_time": trace.get("request", {}).get("max_time"),
                    "servings": trace.get("request", {}).get("servings"),
                },
                "vector_db": {
                    "query_text": trace.get("vector_db", {}).get("query_text"),
                    "candidate_count": len(trace.get("vector_db", {}).get("candidates", [])),
                    "kept_titles": trace.get("vector_db", {}).get("kept_titles", []),
                    "filtered_out_titles": [
                        item.get("title") for item in trace.get("vector_db", {}).get("filtered_out", [])
                    ],
                },
                "context": {
                    "meal_period": trace.get("context", {}).get("time", {}).get("meal_period"),
                    "weather_available": trace.get("context", {}).get("weather", {}).get("available"),
                    "weather_location": trace.get("context", {}).get("weather", {}).get("resolved_location"),
                    "recommendation_style": trace.get("context", {}).get("recommendation_style"),
                },
                "llm": {
                    "model": trace.get("llm", {}).get("model"),
                    "accepted_titles": trace.get("post_processing", {}).get("accepted_titles", []),
                    "rejected_titles": trace.get("post_processing", {}).get("rejected_titles", []),
                },
                "error": trace.get("error"),
            }
        )
    return traces


def load_trace(request_id: str) -> dict[str, Any]:
    if "/" in request_id or "\\" in request_id:
        raise HTTPException(status_code=400, detail="Invalid trace id.")

    path = TRACE_DIR / f"{request_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Trace not found.")

    return json.loads(path.read_text(encoding="utf-8"))


def _json_block(value: Any) -> str:
    return escape(json.dumps(value, indent=2, ensure_ascii=False))


def _text_block(value: Any) -> str:
    return escape(str(value or ""))


def _pill(text: Any, tone: str = "neutral") -> str:
    return f'<span class="pill {tone}">{escape(str(text))}</span>'


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f6f5;
      --surface: #ffffff;
      --surface-soft: #f8faf9;
      --border: #dfe6e2;
      --text: #111827;
      --muted: #5f6f68;
      --primary: #0f7a5a;
      --primary-soft: #e5f5ef;
      --warn: #a16207;
      --warn-soft: #fef3c7;
      --error: #b91c1c;
      --error-soft: #fee2e2;
      --info: #1d4ed8;
      --info-soft: #dbeafe;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
      margin: 0;
    }}
    header {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 1rem 1.5rem;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    header a {{ color: var(--primary); font-weight: 800; text-decoration: none; }}
    main {{ margin: 0 auto; max-width: 1180px; padding: 1.25rem; }}
    h1, h2, h3 {{ line-height: 1.15; margin: 0; }}
    h1 {{ font-size: 1.6rem; }}
    h2 {{ font-size: 1.05rem; }}
    h3 {{ font-size: 0.95rem; }}
    .muted {{ color: var(--muted); }}
    .grid {{ display: grid; gap: 1rem; }}
    .cards {{ grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
      padding: 1rem;
    }}
    .trace-card {{ display: grid; gap: 0.8rem; }}
    .row {{ align-items: center; display: flex; flex-wrap: wrap; gap: 0.5rem; }}
    .split {{ display: grid; gap: 1rem; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
    .pill {{
      background: #eef2f1;
      border: 1px solid var(--border);
      border-radius: 999px;
      color: #31443d;
      display: inline-flex;
      font-size: 0.78rem;
      font-weight: 750;
      padding: 0.22rem 0.55rem;
    }}
    .success {{ background: var(--primary-soft); border-color: #a7dcca; color: var(--primary); }}
    .warning {{ background: var(--warn-soft); border-color: #f4d37a; color: var(--warn); }}
    .danger {{ background: var(--error-soft); border-color: #f4b4b4; color: var(--error); }}
    .info {{ background: var(--info-soft); border-color: #b9d0ff; color: var(--info); }}
    a.button {{
      background: var(--primary);
      border-radius: 6px;
      color: white;
      display: inline-flex;
      font-weight: 800;
      padding: 0.55rem 0.75rem;
      text-decoration: none;
    }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 0.65rem; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }}
    pre {{
      background: #111827;
      border-radius: 8px;
      color: #edf2f7;
      max-height: 520px;
      overflow: auto;
      padding: 1rem;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    details {{ background: var(--surface-soft); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; }}
    summary {{ cursor: pointer; font-weight: 850; }}
    .empty {{ border: 1px dashed var(--border); border-radius: 8px; color: var(--muted); padding: 1rem; }}
    @media (max-width: 820px) {{
      main {{ padding: 0.8rem; }}
      .split {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header><a href="/admin/observability">RecipeAI Observability</a></header>
  <main>{body}</main>
</body>
</html>"""


def render_observability_dashboard(limit: int = 25) -> str:
    traces = list_traces(limit=limit)
    cards: list[str] = []
    for trace in traces:
        request_id = trace.get("request_id")
        error = trace.get("error")
        accepted = trace.get("llm", {}).get("accepted_titles", [])
        rejected = trace.get("llm", {}).get("rejected_titles", [])
        llm_called = bool(accepted or rejected or trace.get("llm", {}).get("model"))
        status = _pill("error", "danger") if error else _pill("ok", "success")
        llm_status = _pill("LLM used", "success") if llm_called else _pill("LLM not reached", "warning")
        weather = trace.get("context", {})
        weather_status = _pill("weather on", "info") if weather.get("weather_available") else _pill("weather off", "warning")
        cards.append(
            f"""<article class="card trace-card">
  <div class="row">{status}{llm_status}{weather_status}{_pill(trace.get('mode'))}</div>
  <div>
    <h2>{escape(str(request_id))}</h2>
    <p class="muted">{escape(str(trace.get('started_at')))}</p>
  </div>
  <div>
    <h3>Vector DB</h3>
    <p>{escape(str(trace.get('vector_db', {}).get('candidate_count')))} candidates, kept {escape(str(len(trace.get('vector_db', {}).get('kept_titles', []))))}</p>
  </div>
  <div>
    <h3>LLM accepted</h3>
    <p>{escape(', '.join(accepted) if accepted else 'None recorded')}</p>
  </div>
  <div>
    <h3>Context</h3>
    <p>{escape(str(weather.get('meal_period')))} · {escape(str(weather.get('recommendation_style')))}</p>
  </div>
  <div class="row">
    <a class="button" href="/admin/traces/{escape(str(request_id))}/ui">Open trace</a>
    <a href="/admin/traces/{escape(str(request_id))}/report">Text report</a>
    <a href="/admin/traces/{escape(str(request_id))}">JSON</a>
  </div>
</article>"""
        )

    body = f"""<section class="grid">
  <div class="card">
    <h1>RAG Observability</h1>
    <p class="muted">Human-readable traces for vector retrieval, augmentation, LLM generation, filtering, and final response.</p>
    <div class="row">
      {_pill(f"{len(traces)} traces", "info")}
      <a href="/admin/traces">Raw trace list JSON</a>
    </div>
  </div>
  <section class="grid cards">{''.join(cards) if cards else '<div class="empty">No traces yet. Make a recipe request first.</div>'}</section>
</section>"""
    return _page("RecipeAI Observability", body)


def render_trace_ui(trace: dict[str, Any]) -> str:
    request = trace.get("request", {})
    context = trace.get("context", {})
    vector_db = trace.get("vector_db", {})
    augmentation = trace.get("augmentation", {})
    llm = trace.get("llm", {})
    post_processing = trace.get("post_processing", {})
    final_response = trace.get("final_response", {})
    error = trace.get("error")

    raw_response = llm.get("raw_response")
    parsed_json = llm.get("parsed_json")
    accepted_titles = post_processing.get("accepted_titles", [])
    rejected_titles = post_processing.get("rejected_titles", [])
    llm_called = bool(raw_response or parsed_json or accepted_titles or rejected_titles)

    candidate_rows = []
    kept_titles = set(vector_db.get("kept_titles", []))
    filtered_by_title = {item.get("title"): item.get("reason") for item in vector_db.get("filtered_out", [])}
    for candidate in vector_db.get("candidates", []):
        title = candidate.get("title")
        kept = title in kept_titles
        candidate_rows.append(
            f"""<tr>
  <td>{escape(str(candidate.get('rank')))}</td>
  <td>{escape(str(title))}</td>
  <td>{escape(str(candidate.get('distance')))}</td>
  <td>{_pill('kept', 'success') if kept else _pill('removed', 'warning')}</td>
  <td>{escape(str(filtered_by_title.get(title, '')))}</td>
</tr>"""
        )

    body = f"""<section class="grid">
  <div class="card">
    <div class="row">
      <a href="/admin/observability">Back to traces</a>
      {_pill('error', 'danger') if error else _pill('ok', 'success')}
      {_pill('LLM used', 'success') if llm_called else _pill('LLM not reached', 'warning')}
      {_pill(request.get('mode'))}
    </div>
    <h1>Trace {escape(str(trace.get('request_id')))}</h1>
    <p class="muted">{escape(str(trace.get('started_at')))} to {escape(str(trace.get('finished_at')))}</p>
  </div>

  <div class="split">
    <section class="card">
      <h2>Request</h2>
      <pre>{_json_block(request)}</pre>
    </section>
    <section class="card">
      <h2>System Time And Weather</h2>
      <pre>{_json_block(context)}</pre>
    </section>
  </div>

  <section class="card">
    <h2>1. Vector DB Retrieval</h2>
    <p><strong>Embedding model:</strong> {escape(str(vector_db.get('embedding_model')))}</p>
    <p><strong>Collection:</strong> {escape(str(vector_db.get('collection')))}</p>
    <p><strong>Embedding query:</strong> {escape(str(vector_db.get('query_text')))}</p>
    <table>
      <thead><tr><th>Rank</th><th>Recipe</th><th>Distance</th><th>Status</th><th>Reason</th></tr></thead>
      <tbody>{''.join(candidate_rows)}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>2. Augmentation</h2>
    <p><strong>Context recipes:</strong> {escape(', '.join(augmentation.get('context_recipe_titles', []) or []))}</p>
    <p><strong>Included fields:</strong> {escape(', '.join(augmentation.get('included_fields', []) or []))}</p>
    <details open>
      <summary>Full prompt sent to LLM</summary>
      <pre>{_text_block(augmentation.get('prompt'))}</pre>
    </details>
  </section>

  <section class="card">
    <h2>3. LLM Generation</h2>
    <div class="row">
      {_pill(f"model: {llm.get('model')}", 'info')}
      {_pill(f"temperature: {llm.get('temperature')}")}
      {_pill(f"max tokens: {llm.get('max_tokens')}")}
      {_pill('raw response captured', 'success') if raw_response else _pill('no raw response', 'warning')}
    </div>
    <div class="split">
      <div>
        <h3>Raw LLM Response</h3>
        <pre>{_text_block(raw_response)}</pre>
      </div>
      <div>
        <h3>Cleaned / Parsed JSON</h3>
        <pre>{_json_block(parsed_json if parsed_json is not None else llm.get('cleaned_response'))}</pre>
      </div>
    </div>
  </section>

  <section class="card">
    <h2>4. Post Processing</h2>
    <p>{escape(str(post_processing.get('rule')))}</p>
    <p><strong>Accepted:</strong> {escape(', '.join(accepted_titles) if accepted_titles else 'None')}</p>
    <p><strong>Rejected:</strong> {escape(', '.join(rejected_titles) if rejected_titles else 'None')}</p>
    <pre>{_json_block(post_processing.get('rejected', []))}</pre>
  </section>

  <section class="card">
    <h2>5. Final Response</h2>
    <p><strong>Returned titles:</strong> {escape(', '.join(final_response.get('recipe_titles', []) or []))}</p>
    <pre>{_json_block(final_response.get('recipes', []))}</pre>
  </section>

  {f'<section class="card"><h2>Error</h2><pre>{_json_block(error)}</pre></section>' if error else ''}
</section>"""
    return _page(f"Trace {trace.get('request_id')}", body)


def render_trace_report(trace: dict[str, Any]) -> str:
    request = trace.get("request", {})
    context = trace.get("context", {})
    vector_db = trace.get("vector_db", {})
    augmentation = trace.get("augmentation", {})
    llm = trace.get("llm", {})
    post_processing = trace.get("post_processing", {})
    final_response = trace.get("final_response", {})

    lines = [
        f"Request ID: {trace.get('request_id')}",
        f"Started: {trace.get('started_at')}",
        f"Finished: {trace.get('finished_at')}",
        f"Mode: {request.get('mode')}",
        "",
        "Input",
        f"- Ingredients: {request.get('ingredients')}",
        f"- Dietary goal: {request.get('dietary_goal')}",
        f"- Max time: {request.get('max_time')}",
        f"- Servings: {request.get('servings')}",
        f"- Token present: {request.get('navigator_token', {}).get('present')}",
        "",
        "System Time And Weather",
        json.dumps(context, indent=2, ensure_ascii=False),
        "",
        "1. Vector DB / Retrieval",
        f"Embedding model: {vector_db.get('embedding_model')}",
        f"Collection: {vector_db.get('collection')}",
        f"Embedding query: {vector_db.get('query_text')}",
        "",
        "ChromaDB candidates:",
    ]

    filtered_by_title = {item.get("title"): item.get("reason") for item in vector_db.get("filtered_out", [])}
    kept_titles = set(vector_db.get("kept_titles", []))
    for candidate in vector_db.get("candidates", []):
        title = candidate.get("title")
        status = "kept" if title in kept_titles else "removed"
        reason = filtered_by_title.get(title)
        distance = candidate.get("distance")
        lines.append(f"- #{candidate.get('rank')} {title} | distance: {distance} | {status}")
        if reason:
            lines.append(f"  Reason: {reason}")

    lines.extend(
        [
            "",
            "Final context sent to LLM:",
        ]
    )
    for title in vector_db.get("kept_titles", []):
        lines.append(f"- {title}")

    lines.extend(
        [
            "",
            "2. Augmentation",
            f"Context recipe count: {augmentation.get('context_recipe_count')}",
            f"Context recipe titles: {augmentation.get('context_recipe_titles')}",
            f"Included fields: {augmentation.get('included_fields')}",
            "",
            "Full prompt sent to LLM:",
            str(augmentation.get("prompt", "")),
            "",
            "3. LLM Generation",
            f"Model: {llm.get('model')}",
            f"Temperature: {llm.get('temperature')}",
            f"Max tokens: {llm.get('max_tokens')}",
            "",
            "Raw LLM response:",
            str(llm.get("raw_response", "")),
            "",
            "Cleaned / parsed response:",
            json.dumps(llm.get("parsed_json", llm.get("cleaned_response", "")), indent=2, ensure_ascii=False),
            "",
            "4. Post Processing",
            f"Rule: {post_processing.get('rule')}",
            f"Accepted titles: {post_processing.get('accepted_titles')}",
            f"Rejected titles: {post_processing.get('rejected_titles')}",
            "",
            "5. Final Response",
            f"Returned titles: {final_response.get('recipe_titles')}",
        ]
    )

    if trace.get("error"):
        lines.extend(["", "Error", json.dumps(trace["error"], indent=2, ensure_ascii=False)])

    return "\n".join(lines)
