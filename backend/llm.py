from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import HTTPException
from openai import APITimeoutError, AsyncOpenAI
from pydantic import ValidationError

from models import Recipe, RecipeRequest
from prompt_builder import build_rag_prompt
from rag import retrieve_recipes

NAVIGATOR_BASE_URL = "https://api.ai.it.ufl.edu/v1/"
LLM_MODEL = "llama-3.1-70b-instruct"


def strip_markdown_fences(text: str) -> str:
    """Remove code fences that some models add despite JSON-only instructions."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:])
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


async def _enrich_recipe(
    client: AsyncOpenAI,
    request: RecipeRequest,
    recipe: dict[str, Any],
    request_context: dict[str, Any] | None,
    trace: Any | None,
) -> Recipe | None:
    """
    Call the LLM for a single recipe, parse, validate, and return it.
    Returns None if the LLM call fails or validation fails, so parallel execution doesn't fully crash.
    """
    prompt = build_rag_prompt(request, recipe, request_context=request_context)
    
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert chef. You always respond with valid JSON objects only. "
                        "Never include explanations or text outside the JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=2000,
            timeout=60,
        )
    except Exception as exc:
        if trace:
            trace.update("llm_errors", {recipe["title"]: str(exc)})
        return None

    raw_text = response.choices[0].message.content or ""
    clean_text = strip_markdown_fences(raw_text)

    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        if trace:
            trace.update("llm_errors", {recipe["title"]: f"JSON Decode Error: {exc}"})
        return None

    if not isinstance(parsed, dict):
        if trace:
            trace.update("llm_errors", {recipe["title"]: "AI response was not a JSON object."})
        return None

    try:
        parsed.setdefault("dish_story", None)
        parsed.setdefault("flavor_profile", None)
        parsed.setdefault("key_technique", None)
        parsed.setdefault("pro_tips", None)
        parsed.setdefault("ingredient_insights", None)
        parsed.setdefault("serving_suggestion", None)
        parsed.setdefault("estimated_difficulty", None)
        parsed.setdefault("estimated_time_breakdown", None)
        # Ensure the LLM didn't hallucinate the title
        parsed["title"] = recipe["title"]
        return Recipe(**parsed)
    except ValidationError as exc:
        if trace:
            trace.update("llm_errors", {recipe["title"]: f"Validation Error: {exc}"})
        return None


async def get_recommendations(request: RecipeRequest, trace: Any | None = None) -> tuple[list[Recipe], int]:
    """
    Run the complete RAG pipeline and return validated recipe recommendations using parallel LLM processing.
    """
    n_results = 1 if request.mode == "daily" else 3
    request_context = trace.data.get("context") if trace else None
    
    retrieved = retrieve_recipes(request, n_results=n_results, trace=trace, request_context=request_context)
    if not retrieved:
        raise HTTPException(
            status_code=404,
            detail="No recipes found in database. Please run ingest.py first.",
        )

    if trace:
        trace.update(
            "augmentation",
            {
                "context_recipe_count": len(retrieved),
                "context_recipe_titles": [r["title"] for r in retrieved],
            },
        )
        trace.update(
            "llm",
            {
                "base_url": NAVIGATOR_BASE_URL,
                "model": LLM_MODEL,
                "temperature": 0.5,
                "max_tokens": 2000,
                "timeout_seconds": 60,
                "parallel_requests": len(retrieved),
            },
        )

    client = AsyncOpenAI(api_key=request.navigator_token, base_url=NAVIGATOR_BASE_URL)

    # Launch concurrent requests for all retrieved recipes
    tasks = [
        _enrich_recipe(client, request, recipe, request_context, trace)
        for recipe in retrieved
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failures and exceptions
    accepted_recipes = []
    for r in results:
        if isinstance(r, Recipe):
            accepted_recipes.append(r)
        elif isinstance(r, Exception):
            if trace:
                trace.update("llm_errors", {"unhandled_exception": str(r)})
            # We don't raise here so partial successes still return to the user!

    if not accepted_recipes:
        raise HTTPException(
            status_code=502,
            detail="NaviGator API failed to generate valid recommendations for all recipes. It may be rate limited or timing out.",
        )

    return accepted_recipes, len(retrieved)
