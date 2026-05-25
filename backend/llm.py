from __future__ import annotations

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


async def get_recommendations(request: RecipeRequest, trace: Any | None = None) -> tuple[list[Recipe], int]:
    """
    Run the complete RAG pipeline and return validated recipe recommendations.
    """
    n_results = 1 if request.mode == "daily" else 3
    request_context = trace.data.get("context") if trace else None
    retrieved = retrieve_recipes(request, n_results=n_results, trace=trace, request_context=request_context)
    if not retrieved:
        raise HTTPException(
            status_code=404,
            detail="No recipes found in database. Please run ingest.py first.",
        )

    prompt = build_rag_prompt(request, retrieved, request_context=request_context)
    if trace:
        trace.update(
            "augmentation",
            {
                "context_recipe_count": len(retrieved),
                "context_recipe_titles": [recipe["title"] for recipe in retrieved],
                "included_fields": ["title", "time", "servings", "calories", "tags", "ingredients", "description", "steps"],
                "prompt": prompt,
            },
        )
        trace.update(
            "llm",
            {
                "base_url": NAVIGATOR_BASE_URL,
                "model": LLM_MODEL,
                "temperature": 0.5,
                "max_tokens": 2000,
                "timeout_seconds": 30,
            },
        )

    client = AsyncOpenAI(api_key=request.navigator_token, base_url=NAVIGATOR_BASE_URL)

    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert chef. You always respond with valid JSON arrays only. "
                        "Never include explanations or text outside the JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=4000,
            timeout=60,
        )
    except APITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="NaviGator request timed out. Please try again.",
        ) from exc
    except Exception as exc:
        error_msg = str(exc)
        lowered = error_msg.lower()
        if "401" in error_msg or "unauthorized" in lowered:
            raise HTTPException(
                status_code=401,
                detail="Invalid NaviGator API token. Please check your token and try again.",
            ) from exc
        if "429" in error_msg or "rate limit" in lowered:
            raise HTTPException(
                status_code=429,
                detail="NaviGator rate limit reached. Please wait a moment and try again.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"NaviGator API error: {error_msg}") from exc

    raw_text = response.choices[0].message.content or ""
    clean_text = strip_markdown_fences(raw_text)
    if trace:
        trace.update("llm", {"raw_response": raw_text, "cleaned_response": clean_text})

    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        if trace:
            trace.update("llm", {"parse_error": str(exc)})
        raise HTTPException(status_code=500, detail="AI returned malformed JSON. Please try again.") from exc

    if not isinstance(parsed, list):
        if trace:
            trace.update("llm", {"parsed_type": type(parsed).__name__})
        raise HTTPException(status_code=500, detail="AI response was not a JSON array. Please try again.")

    if trace:
        trace.update("llm", {"parsed_json": parsed})

    try:
        mapped_recipes = []
        for recipe_data in parsed:
            recipe_data.setdefault("dish_story", None)
            recipe_data.setdefault("flavor_profile", None)
            recipe_data.setdefault("key_technique", None)
            recipe_data.setdefault("pro_tips", None)
            recipe_data.setdefault("ingredient_insights", None)
            recipe_data.setdefault("serving_suggestion", None)
            recipe_data.setdefault("estimated_difficulty", None)
            recipe_data.setdefault("estimated_time_breakdown", None)
            mapped_recipes.append(Recipe(**recipe_data))
        recipes = mapped_recipes
    except ValidationError as exc:
        if trace:
            trace.update("llm", {"validation_error": str(exc)})
        raise HTTPException(
            status_code=500,
            detail=f"AI response did not match expected recipe format: {exc}",
        ) from exc

    retrieved_titles = {recipe["title"].strip().lower() for recipe in retrieved}
    accepted_recipes = [recipe for recipe in recipes if recipe.title.strip().lower() in retrieved_titles]
    rejected_recipes = [recipe for recipe in recipes if recipe.title.strip().lower() not in retrieved_titles]

    if trace:
        trace.update(
            "post_processing",
            {
                "rule": "Only recipes retrieved from ChromaDB context are allowed in final response.",
                "accepted_titles": [recipe.title for recipe in accepted_recipes],
                "rejected_titles": [recipe.title for recipe in rejected_recipes],
                "rejected": [
                    {
                        "title": recipe.title,
                        "reason": "LLM returned a recipe that was not in the retrieved context.",
                    }
                    for recipe in rejected_recipes
                ],
            },
        )

    return accepted_recipes, len(retrieved)
