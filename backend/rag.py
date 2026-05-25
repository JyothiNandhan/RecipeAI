from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.errors import NotFoundError
from fastapi import HTTPException

from models import RecipeRequest
from request_context import context_summary

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = str(BASE_DIR / "chroma_db")
COLLECTION_NAME = "recipes"
MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Ingredient alias expansion — maps user shorthand to recipe vocabulary
# ---------------------------------------------------------------------------
INGREDIENT_ALIASES: dict[str, set[str]] = {
    "chillies": {"chili flakes", "chiles", "chilies", "chili"},
    "chilies": {"chili flakes", "chiles", "chillies", "chili"},
    "chili": {"chili flakes", "chillies", "chilies", "chiles"},
    "noodles": {"pasta", "spaghetti", "fettuccine", "linguine"},
    "pasta": {"noodles", "spaghetti", "fettuccine", "linguine"},
    "spring onion": {"scallion", "green onion"},
    "scallion": {"spring onion", "green onion"},
    "bell pepper": {"bell peppers", "capsicum"},
    "bell peppers": {"bell pepper", "capsicum"},
    "coconut": {"coconut milk", "coconut cream"},
    "yoghurt": {"yogurt"},
    "yogurt": {"yoghurt"},
    "bread": {"toast", "sourdough", "baguette", "pita", "bun", "roll"},
    "toast": {"bread", "sourdough"},
    "pita": {"bread", "flatbread"},
}

# ---------------------------------------------------------------------------
# Strict main proteins — used to prevent protein mismatches
# ---------------------------------------------------------------------------
STRICT_MAIN_INGREDIENTS = {
    "beef", "chicken", "eggs", "fish", "pork",
    "salmon", "shrimp", "tofu", "turkey", "lamb",
    "tuna", "crab", "lobster", "duck",
}

# ---------------------------------------------------------------------------
# Base staples — when a user selects one of these AND the recipe uses it,
# the strict protein filter is relaxed so good matches are not discarded.
# ---------------------------------------------------------------------------
BASE_STAPLES = {
    "bread", "toast", "sourdough", "baguette", "pita", "wrap", "roll",
    "pasta", "noodles", "spaghetti", "rice", "quinoa", "oats", "flour",
    "tortillas", "tortilla", "couscous", "polenta", "barley",
}

_model: object | None = None
_chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


# ---------------------------------------------------------------------------
# Lazy model loader — SentenceTransformer backed by PyTorch
# ---------------------------------------------------------------------------
def get_model() -> object:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        try:
            _model = SentenceTransformer(MODEL_NAME, local_files_only=True)
        except (TypeError, OSError):
            _model = SentenceTransformer(MODEL_NAME)
    return _model


# ---------------------------------------------------------------------------
# Query builder — richer natural-language queries for better semantic recall
# ---------------------------------------------------------------------------
def build_query_text(
    request: RecipeRequest, request_context: dict[str, Any] | None = None
) -> str:
    """
    Build a descriptive natural-language query that SentenceTransformer
    can embed into a meaningful vector for ChromaDB similarity search.
    Ingredients are repeated with context to increase recall weight.
    """
    context_text = (
        f" {context_summary(request_context)}" if request_context else ""
    )

    if request.mode == "ingredients":
        ingredients = request.ingredients or []
        if not ingredients:
            return f"delicious recipe{context_text}"

        # Identify base staples to anchor the query
        norm = [i.strip().lower() for i in ingredients]
        bases = [i for i in norm if i in BASE_STAPLES]
        proteins = [i for i in norm if i in STRICT_MAIN_INGREDIENTS]
        others = [i for i in norm if i not in BASE_STAPLES and i not in STRICT_MAIN_INGREDIENTS]

        parts: list[str] = []
        if bases:
            parts.append(f"{', '.join(bases)}-based dish")
        if proteins:
            parts.append(f"with {', '.join(proteins)}")
        if others:
            parts.append(f"using {', '.join(others)}")

        ingredient_phrase = " ".join(parts) if parts else f"using {', '.join(norm)}"
        # Repeat ingredients to amplify their semantic weight
        all_ings = ", ".join(norm)
        return (
            f"recipe {ingredient_phrase}. "
            f"Ingredients available: {all_ings}.{context_text}"
        )

    if request.mode == "preferences":
        parts_pref: list[str] = []
        if request.dietary_goal:
            parts_pref.append(request.dietary_goal)
        if request.max_time:
            parts_pref.append(f"under {request.max_time} minutes")
        if request.servings:
            parts_pref.append(f"serves {request.servings} people")
        query = "recipe " + " ".join(parts_pref) if parts_pref else "healthy recipe"
        return f"{query}.{context_text}"

    return (
        f"inspiring {context_summary(request_context) if request_context else 'delicious'} "
        f"recipe of the day{context_text}"
    )


# ---------------------------------------------------------------------------
# Metadata deserialiser
# ---------------------------------------------------------------------------
def _deserialize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": metadata["title"],
        "emoji": metadata["emoji"],
        "time": metadata["time"],
        "servings": metadata["servings"],
        "calories": metadata["calories"],
        "ingredients": json.loads(str(metadata["ingredients"])),
        "steps": json.loads(str(metadata["steps"])),
        "tags": json.loads(str(metadata["tags"])),
        "description": metadata["description"],
        "dietary": json.loads(str(metadata.get("dietary", "[]"))),
    }


# ---------------------------------------------------------------------------
# Ingredient normalisation & alias expansion
# ---------------------------------------------------------------------------
def _normalize_ingredient(ingredient: str) -> str:
    return ingredient.strip().lower()


def _selected_ingredient_set(request: RecipeRequest) -> set[str]:
    """Expand selected ingredients with their aliases."""
    selected = {_normalize_ingredient(i) for i in request.ingredients or []}
    expanded = set(selected)
    for ingredient in selected:
        expanded.update(INGREDIENT_ALIASES.get(ingredient, set()))
    return expanded


# ---------------------------------------------------------------------------
# Smart filter with overlap scoring
# ---------------------------------------------------------------------------
def _score_and_filter(
    recipe: dict[str, Any],
    selected: set[str],
) -> tuple[str | None, int]:
    """
    Returns (filter_reason | None, overlap_count).

    Filter rules (in priority order):
      1. Must share at least 1 selected ingredient — hard rule.
      2. Strict protein check is RELAXED when:
           a) User selected a BASE_STAPLE that appears in the recipe  — bread,
              pasta, rice, etc. are the real primary ingredient; a secondary
              protein like eggs shouldn't disqualify the recipe.
           b) OR overlap count >= 2 — strong multi-ingredient match implies
              the user has most of what they need.
      3. Otherwise, a recipe that contains an unselected STRICT protein is
         filtered out to avoid recommending something the user can't make.
    """
    recipe_ingredients = {
        _normalize_ingredient(i) for i in recipe["ingredients"]
    }

    def _match_any(word_set: set[str], text_list: set[str]) -> set[str]:
        found = set()
        for w in word_set:
            if any(re.search(r'\b' + re.escape(w) + r'\b', t) for t in text_list):
                found.add(w)
        return found

    overlap = _match_any(selected, recipe_ingredients)
    overlap_count = len(overlap)

    # Hard rule: zero overlap → irrelevant
    if overlap_count == 0:
        return "does not include any selected ingredient", 0

    # Which selected BASE_STAPLES appear in this recipe?
    selected_bases_in_recipe = overlap.intersection(BASE_STAPLES)

    # Unselected strict proteins this recipe requires
    recipe_proteins = _match_any(STRICT_MAIN_INGREDIENTS, recipe_ingredients)
    missing_proteins = recipe_proteins - selected

    if missing_proteins:
        # Relax: user selected a base staple that IS in this recipe
        if selected_bases_in_recipe:
            return None, overlap_count

        # Relax: recipe shares >= 2 selected ingredients (strong match)
        if overlap_count >= 2:
            return None, overlap_count

        missing = ", ".join(sorted(missing_proteins))
        return f"contains unselected main ingredient: {missing}", overlap_count

    return None, overlap_count


def _ingredient_filter_reason(
    recipe: dict[str, Any], selected: set[str]
) -> str | None:
    reason, _ = _score_and_filter(recipe, selected)
    return reason


def _matches_selected_ingredients(
    recipe: dict[str, Any], selected: set[str]
) -> bool:
    return _ingredient_filter_reason(recipe, selected) is None


# ---------------------------------------------------------------------------
# Main retrieval function
# ---------------------------------------------------------------------------
def retrieve_recipes(
    request: RecipeRequest,
    n_results: int = 5,
    trace: Any | None = None,
    request_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Full RAG retrieval pipeline:
      1. Build a rich query string from the user's request.
      2. Embed it with SentenceTransformer (PyTorch backend).
      3. Query ChromaDB for semantically similar recipes.
      4. Apply smart ingredient filtering (relax for base staples).
      5. Re-rank kept recipes by ingredient overlap score descending.
      6. Return top N.
    """
    query_text = build_query_text(request, request_context=request_context)

    # Step 1 & 2: embed query using SentenceTransformer / PyTorch
    query_embedding = get_model().encode(query_text).tolist()  # type: ignore[attr-defined]

    if trace:
        trace.update(
            "vector_db",
            {
                "collection": COLLECTION_NAME,
                "embedding_model": MODEL_NAME,
                "query_text": query_text,
                "requested_results": n_results,
            },
        )

    # Step 3: ChromaDB vector similarity search
    try:
        collection = _chroma_client.get_collection(COLLECTION_NAME)
    except (ValueError, NotFoundError) as exc:
        raise HTTPException(
            status_code=404,
            detail="No recipes found in database. Please run ingest.py first.",
        ) from exc

    # Retrieve a wider pool so filtering has enough candidates
    query_count = max(n_results * 4, 20) if request.mode == "ingredients" else max(n_results, 10)
    if trace:
        trace.update("vector_db", {"chroma_query_count": query_count})

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=query_count,
        include=["metadatas", "distances"],
    )

    metadatas = results.get("metadatas") or [[]]
    distances = results.get("distances") or [[]]
    recipes = [_deserialize_metadata(m) for m in metadatas[0]]

    candidate_records = [
        {
            "rank": idx + 1,
            "title": recipe["title"],
            "distance": float(distances[0][idx]) if idx < len(distances[0]) else None,
            "ingredients": recipe["ingredients"],
            "tags": recipe["tags"],
        }
        for idx, recipe in enumerate(recipes)
    ]

    # Step 4 & 5: filter + re-rank by overlap score
    filtered_out: list[dict[str, Any]] = []
    kept_with_scores: list[tuple[dict[str, Any], int]] = []

    if request.mode == "ingredients":
        selected = _selected_ingredient_set(request)
        for recipe in recipes:
            reason, overlap_count = _score_and_filter(recipe, selected)
            if reason:
                filtered_out.append({"title": recipe["title"], "reason": reason})
            else:
                kept_with_scores.append((recipe, overlap_count))

        # Re-rank: higher overlap first, then preserve ChromaDB distance order
        kept_with_scores.sort(key=lambda x: x[1], reverse=True)
        recipes = [r for r, _ in kept_with_scores]
    # For preferences/daily modes, ChromaDB order (semantic distance) is sufficient

    final_recipes = recipes[:n_results]

    if trace:
        trace.update(
            "vector_db",
            {
                "candidates": candidate_records,
                "filtered_out": filtered_out,
                "kept_titles": [r["title"] for r in final_recipes],
                "kept_context": [
                    {
                        "title": r["title"],
                        "time": r["time"],
                        "servings": r["servings"],
                        "calories": r["calories"],
                        "ingredients": r["ingredients"],
                        "tags": r["tags"],
                        "description": r["description"],
                    }
                    for r in final_recipes
                ],
            },
        )

    return final_recipes
