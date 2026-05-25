from __future__ import annotations

import json
from typing import Any

from models import RecipeRequest
from request_context import context_summary


def build_rag_prompt(
    request: RecipeRequest,
    retrieved_recipes: list[dict[str, Any]],
    request_context: dict[str, Any] | None = None,
) -> str:
    """
    Build the RAG prompt with user intent, retrieved recipe context, and JSON-only output rules.
    """
    context_blocks: list[str] = []
    for index, recipe in enumerate(retrieved_recipes, 1):
        block = (
            f"Recipe {index}: {recipe['title']} {recipe['emoji']}\n"
            f"  Time: {recipe['time']} minutes | Servings: {recipe['servings']} | Calories: {recipe['calories']} kcal\n"
            f"  Tags: {', '.join(recipe['tags'])}\n"
            f"  Ingredients: {', '.join(recipe['ingredients'])}\n"
            f"  Description: {recipe['description']}\n"
            f"  Steps: {'; '.join(recipe['steps'])}"
        )
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    if request.mode == "ingredients":
        user_request = f"I have these ingredients: {', '.join(request.ingredients or [])}. What can I cook?"
    elif request.mode == "preferences":
        parts: list[str] = []
        if request.dietary_goal:
            parts.append(f"dietary goal: {request.dietary_goal}")
        if request.max_time:
            parts.append(f"max cooking time: {request.max_time} minutes")
        if request.servings:
            parts.append(f"servings needed: {request.servings}")
        user_request = "I want a recipe with: " + ", ".join(parts)
    else:
        user_request = "Surprise me with an inspiring recipe of the day."

    environment = context_summary(request_context) if request_context else "No time or weather context available."

    json_schema = json.dumps(
        [
            {
                "title": "string",
                "emoji": "string (one emoji)",
                "time": "integer (minutes)",
                "servings": "integer",
                "calories": "integer",
                "ingredients": ["list of strings"],
                "steps": ["list of strings, ordered"],
                "tags": ["list of strings"],
                "description": "string (1-2 sentences)",
                "match_reason": "string (why this fits the user's request)",
                "dish_story": "string",
                "flavor_profile": "string",
                "key_technique": "string",
                "pro_tips": ["list of strings"],
                "ingredient_insights": "string",
                "serving_suggestion": "string",
                "estimated_difficulty": "string",
                "estimated_time_breakdown": {
                    "prep_minutes": "integer",
                    "cook_minutes": "integer"
                }
            }
        ],
        indent=2,
    )

    return f"""You are a world-class chef and passionate food writer with deep knowledge of global cuisines, cooking techniques, flavor science, and culinary history. You will be given a list of {len(retrieved_recipes)} recipes that have already been selected as good matches for the user. Your only job is to explain ALL {len(retrieved_recipes)} recipes beautifully and in detail so that the person reading feels genuinely excited to cook them and fully understands what they are making and why it will be delicious. You are not selecting or filtering recipes. You are enriching and explaining the recipes you are given.

For EVERY single recipe provided in the list below, you MUST return a corresponding JSON object with exactly these fields:

dish_story: Three sentences on the cultural and historical background of this dish. Where it comes from, what tradition it belongs to, why it is cooked this way. Must contain a real specific fact, not a vague description. Never write a Wikipedia style summary.

flavor_profile: Two sentences describing exactly what this dish tastes like. Describe the dominant flavors, the texture, the aroma, and what makes it satisfying. Be specific and vivid. Make the person's mouth water.

key_technique: Three sentences on the single most important cooking technique for this dish. What is the one thing a home cook must get right. What is the most common mistake and how to avoid it. What separates a decent version from a truly great one.

pro_tips: An array of exactly three short specific actionable tips that elevate this dish. Each tip must be one to two sentences. No generic advice like season to taste. Every tip must be something a professional chef would actually tell you standing next to you at the stove.

ingredient_insights: Two sentences explaining why the key ingredients in this dish work together. Explain the food science or culinary logic behind the combination in plain simple language that a home cook can understand and appreciate.

serving_suggestion: Two sentences on how to plate and serve this dish properly. What to serve alongside it, what drink pairs well, and how to make it look as good as it tastes.

estimated_difficulty: Return exactly one of these three values: beginner, intermediate, or advanced. Be honest. Do not call everything beginner.

estimated_time_breakdown: A JSON object with exactly two keys: prep_minutes as an integer and cook_minutes as an integer. These must be realistic and specific to this dish.

Return only a valid raw JSON array containing exactly {len(retrieved_recipes)} objects (one for each recipe provided). No preamble. No markdown code fences. No explanation outside the JSON. If you return anything other than raw valid JSON the entire system will break.

QUALITY STANDARDS — these are non-negotiable:

Bad dish_story: This is an Italian dish that is popular worldwide.
Good dish_story: Tuscan-style chicken dishes trace their roots to the cucina povera tradition of Tuscany, where peasant cooks transformed humble ingredients into deeply satisfying meals using nothing more than olive oil, garlic, and whatever vegetables were in season. The addition of cream is a more modern adaptation that became popular in Italian-American restaurants in the 1980s and has since become a weeknight staple in home kitchens worldwide. The name alla cacciatora literally means in the style of the hunter, referring to the rustic one-pan cooking method used by hunters who needed to cook over an open fire.

Bad key_technique: Make sure to cook the chicken properly.
Good key_technique: The single most important step is getting a proper sear on the chicken before building the sauce. Pat the chicken completely dry with paper towels before it hits the pan because any surface moisture will steam the meat instead of browning it and you will never get that golden crust. You want the pan hot enough that the chicken releases naturally after four to five minutes without sticking, which tells you the Maillard reaction has completed and the crust has properly formed.

Bad pro_tips entry: Cook on medium heat.
Good pro_tips entry: Deglaze the pan with a splash of white wine or chicken broth immediately after searing the chicken and use a wooden spoon to scrape up every browned bit from the bottom — those caramelized bits are called fond and they are the deepest source of flavor in the entire dish.

Every single field must meet this quality bar. No exceptions.

AVAILABLE RECIPES TO ENRICH:
{context}

REQUIRED JSON FORMAT (Must contain all these fields):
{json_schema}
"""
