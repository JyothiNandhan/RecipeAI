"""
Recipe Database Fetcher for the RAG Recipe App.

Combines recipes from three open sources into one unified recipes.json.
Run this once before running ingest.py.

Sources:
  A) Wikibooks Cookbook (~1,000 recipes, CC-BY-SA)
     Download first: python -c "from datasets import load_dataset; ds = load_dataset('gossminn/wikibooks-cookbook'); ds['main'].to_json('wikibooks_recipes.json')"

  B) TheMealDB (~300 food recipes, free API, no key needed)
     Fetched automatically by this script.

  C) TheCocktailDB (~600 drink recipes, free API, no key needed)
     Fetched automatically by this script.

  D) Epicurious (~13,500 recipes, scraped dataset)
     Download first: git clone https://github.com/josephrmartinez/recipe-dataset epicurious_data

Usage:
    # Full run (all three sources)
    python fetch_all_recipes.py

    # Skip Epicurious (if not downloaded)
    python fetch_all_recipes.py --skip-epicurious

    # Quick test run with only 100 Epicurious recipes
    python fetch_all_recipes.py --epicurious-limit 100

    # Custom output path
    python fetch_all_recipes.py --output data/my_recipes.json

After running:
    python ingest.py
    uvicorn main:app --reload
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

THEMEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"
COCKTAILDB_BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"

DRINK_EMOJI_MAP: list[tuple[list[str], str]] = [
    (["martini", "gin"], "🍸"),
    (["margarita", "daiquiri", "sour"], "🍹"),
    (["beer", "ale", "lager"], "🍺"),
    (["wine", "sangria", "champagne", "prosecco"], "🍷"),
    (["shot", "shooter"], "🥃"),
    (["coffee", "espresso", "latte"], "☕"),
    (["juice", "lemonade", "punch", "smoothie"], "🥤"),
    (["milk", "cream", "shake"], "🥛"),
    (["tropical", "pina colada", "mai tai", "mango"], "🌴"),
    (["whiskey", "bourbon", "scotch", "rum", "vodka", "tequila"], "🥃"),
    (["cider", "mead"], "🍺"),
]

TAG_RULES: list[tuple[list[str], str]] = [
    (["pasta", "spaghetti", "penne", "linguine", "risotto", "gnocchi", "lasagna"], "Italian"),
    (["tortilla", "taco", "burrito", "jalapeño", "jalapeno", "chipotle", "salsa", "enchilada"], "Mexican"),
    (["soy sauce", "miso", "dashi", "ramen", "udon", "teriyaki", "wasabi"], "Japanese"),
    (["curry", "masala", "tikka", "ghee", "naan", "paneer", "garam"], "Indian"),
    (["tahini", "hummus", "falafel", "shakshuka", "za'atar", "sumac"], "Middle Eastern"),
    (["olive oil", "feta", "pita", "halloumi", "oregano", "tzatziki"], "Mediterranean"),
    (["wok", "bok choy", "hoisin", "oyster sauce", "five spice", "dim sum"], "Chinese"),
    (["coconut milk", "lemongrass", "fish sauce", "galangal", "thai basil"], "Thai"),
    (["soup", "broth", "stew", "chowder", "bisque"], "Soup"),
    (["salad", "lettuce", "arugula", "kale", "spinach"], "Salad"),
    (["baked", "roasted", "oven"], "Baked"),
    (["grilled", "barbecue", "bbq", "charred"], "Grilled"),
    (["fried", "deep-fried", "pan-fried", "crispy"], "Fried"),
    (["smoothie", "juice", "shake", "blend"], "Drink"),
    (["cake", "cookie", "brownie", "dessert", "pudding", "pie", "muffin", "tart", "pastry"], "Dessert"),
]

MEAT_KEYWORDS = [
    "chicken",
    "beef",
    "pork",
    "lamb",
    "turkey",
    "bacon",
    "sausage",
    "ham",
    "veal",
    "duck",
    "shrimp",
    "salmon",
    "tuna",
    "fish",
    "anchovy",
    "crab",
    "lobster",
    "prawn",
]
DAIRY_KEYWORDS = [
    "milk",
    "cream",
    "butter",
    "cheese",
    "yogurt",
    "mozzarella",
    "parmesan",
    "brie",
    "cheddar",
    "feta",
    "ghee",
    "whey",
    "lactose",
]
GLUTEN_KEYWORDS = [
    "flour",
    "bread",
    "pasta",
    "soy sauce",
    "wheat",
    "barley",
    "rye",
    "semolina",
    "couscous",
    "bulgur",
    "breadcrumbs",
    "croutons",
    "tortilla",
    "pita",
]
EGG_KEYWORDS = ["egg", "eggs", "egg yolk", "egg white"]

EMOJI_MAP: list[tuple[list[str], str]] = [
    (["pasta", "spaghetti", "linguine", "penne", "lasagna"], "🍝"),
    (["pizza"], "🍕"),
    (["burger", "hamburger"], "🍔"),
    (["taco", "burrito", "quesadilla"], "🌮"),
    (["sushi", "roll", "maki"], "🍱"),
    (["curry", "masala", "tikka"], "🍛"),
    (["soup", "stew", "broth", "chowder"], "🍲"),
    (["salad"], "🥗"),
    (["sandwich", "toast", "bruschetta"], "🥪"),
    (["cake", "cupcake", "muffin"], "🍰"),
    (["cookie", "brownie", "biscuit"], "🍪"),
    (["pancake", "waffle", "crepe"], "🥞"),
    (["egg", "omelette", "frittata", "shakshuka"], "🍳"),
    (["chicken"], "🍗"),
    (["fish", "salmon", "tuna", "seafood", "shrimp"], "🐟"),
    (["steak", "beef", "meat"], "🥩"),
    (["rice", "risotto", "pilaf"], "🍚"),
    (["bread", "loaf", "focaccia"], "🍞"),
    (["smoothie", "juice", "shake"], "🥤"),
    (["ice cream", "gelato", "sorbet"], "🍨"),
    (["pie", "tart"], "🥧"),
    (["wrap", "burrito", "tortilla"], "🌯"),
    (["stir fry", "wok"], "🥘"),
    (["noodle", "ramen", "udon", "pho"], "🍜"),
    (["hummus", "dip", "guacamole"], "🥙"),
]

CALORIE_SIGNALS: dict[str, int] = {
    "butter": 200,
    "cream": 180,
    "heavy cream": 200,
    "cheese": 150,
    "parmesan": 130,
    "mozzarella": 120,
    "olive oil": 100,
    "oil": 90,
    "coconut milk": 80,
    "pasta": 160,
    "rice": 150,
    "flour": 140,
    "bread": 120,
    "potato": 100,
    "sweet potato": 90,
    "beef": 180,
    "pork": 170,
    "lamb": 190,
    "chicken": 140,
    "salmon": 130,
    "sausage": 200,
    "bacon": 180,
    "egg": 70,
    "eggs": 140,
    "sugar": 100,
    "honey": 80,
    "chocolate": 160,
    "nuts": 120,
    "peanut butter": 180,
    "avocado": 80,
    "coconut": 90,
    "spinach": 10,
    "lettuce": 5,
    "cucumber": 8,
    "tomato": 15,
    "tomatoes": 15,
    "onion": 20,
    "garlic": 5,
    "lemon": 8,
    "lime": 8,
    "herbs": 5,
    "spices": 5,
    "broth": 20,
    "stock": 20,
    "water": 0,
    "vinegar": 3,
    "mushroom": 15,
    "mushrooms": 15,
    "pepper": 5,
    "zucchini": 12,
    "celery": 5,
    "carrot": 20,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and combine recipes from Wikibooks, TheMealDB, TheCocktailDB, and Epicurious.")
    parser.add_argument("--output", type=str, default="recipes.json", help="Output JSON file path (default: recipes.json)")
    parser.add_argument("--skip-wikibooks", action="store_true", help="Skip Wikibooks source")
    parser.add_argument("--skip-themealdb", action="store_true", help="Skip TheMealDB source")
    parser.add_argument("--skip-cocktaildb", action="store_true", help="Skip TheCocktailDB source")
    parser.add_argument("--skip-epicurious", action="store_true", help="Skip Epicurious source (if file not downloaded)")
    parser.add_argument("--wikibooks-file", type=str, default="wikibooks_recipes.json", help="Path to wikibooks_recipes.json")
    parser.add_argument("--epicurious-file", type=str, default="epicurious_data/recipes.json", help="Path to epicurious recipes.json")
    parser.add_argument("--epicurious-limit", type=int, default=None, help="Limit Epicurious to first N recipes (useful for testing)")
    return parser.parse_args()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return (slug[:60].strip("-") or "recipe")


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\x00", " ")).strip()


def split_instructions(text: str) -> list[str]:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return []

    parts = [part.strip(" \t-*0123456789.)") for part in raw.split("\n")]
    steps = [part for part in parts if len(part) >= 10]
    if len(steps) < 2:
        parts = re.split(r"\.\s+", raw)
        steps = [part.strip(" \t-*0123456789.)") for part in parts if len(part.strip()) >= 10]

    normalized: list[str] = []
    for step in steps:
        step = clean_text(step)
        if not step:
            continue
        if step[-1] not in ".!?":
            step = f"{step}."
        normalized.append(step)
    return normalized


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def infer_dietary(ingredients: list[str]) -> list[str]:
    combined = " ".join(ingredients).lower()
    has_meat_or_fish = contains_any(combined, MEAT_KEYWORDS)
    has_dairy = contains_any(combined, DAIRY_KEYWORDS)
    has_gluten = contains_any(combined, GLUTEN_KEYWORDS)
    has_eggs = contains_any(combined, EGG_KEYWORDS)
    has_quantity = bool(re.search(r"\b\d+(\.\d+)?\s*(g|kg|oz|lb|lbs|fillets?|pieces?|cups?|tbsp|tsp)\b", combined))

    labels: list[str] = []
    if not has_meat_or_fish and not has_eggs and not has_dairy:
        labels.extend(["Vegan", "Vegetarian"])
    elif not has_meat_or_fish:
        labels.append("Vegetarian")

    if not has_gluten:
        labels.append("Gluten-free")
    if (has_meat_or_fish or has_eggs) and has_quantity:
        labels.append("High protein")

    return dedupe_preserve_order(labels)


def infer_tags(title: str, ingredients: list[str], dietary: list[str], time_minutes: int | None = None) -> list[str]:
    combined = f"{title} {' '.join(ingredients)}".lower()
    tags = list(dietary)

    for keywords, tag in TAG_RULES:
        if contains_any(combined, keywords):
            tags.append(tag)

    if time_minutes is not None and time_minutes <= 25:
        tags.append("Quick")

    return dedupe_preserve_order(tags)


def infer_emoji(title: str, tags: list[str]) -> str:
    combined = f"{title} {' '.join(tags)}".lower()
    for keywords, emoji in EMOJI_MAP:
        if contains_any(combined, keywords):
            return emoji
    return "🍽️"


def estimate_time(title: str, ingredients: list[str], steps: list[str]) -> int:
    title_text = title.lower()
    step_text = " ".join(steps).lower()

    if "slow cooker" in step_text or "overnight" in step_text:
        return 480
    if contains_any(step_text, ["bake", "roast", "oven"]):
        return 45
    if contains_any(step_text, ["simmer", "braise", "stew"]):
        return 40
    if contains_any(title_text, ["quick", "fast", "15-minute"]):
        return 15
    if len(steps) <= 3:
        return 15
    if len(ingredients) <= 4:
        return 20
    return 30


def estimate_calories(ingredients: list[str], servings: int) -> int:
    base = 150
    for ingredient in ingredients:
        lower = ingredient.lower()
        for signal, calories in CALORIE_SIGNALS.items():
            if signal in lower:
                base += calories
                break

    per_serving = int(base / max(servings, 1))
    return max(80, min(per_serving, 1200))


def estimate_servings(title: str, ingredients: list[str]) -> int:
    lower = title.lower()
    if contains_any(lower, ["party", "crowd", "large batch"]):
        return 8
    if len(ingredients) >= 10:
        return 4
    if len(ingredients) >= 6:
        return 3
    return 2


def truncate(text: str, max_length: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 1].rstrip() + "…"


def first_sentence(text: str, max_length: int = 120) -> str:
    cleaned = clean_text(text)
    match = re.search(r"(.+?[.!?])(?:\s|$)", cleaned)
    sentence = match.group(1) if match else cleaned
    return truncate(sentence, max_length)


def build_recipe(
    title: str,
    ingredients: list[str],
    steps: list[str],
    servings: int,
    description: str,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    dietary = infer_dietary(ingredients)
    time_minutes = estimate_time(title, ingredients, steps)
    tags = infer_tags(title, ingredients, dietary, time_minutes)
    for tag in extra_tags or []:
        cleaned = clean_text(tag)
        if cleaned:
            tags.append(cleaned)
    tags = dedupe_preserve_order(tags)

    return {
        "title": clean_text(title),
        "emoji": infer_emoji(title, tags),
        "time": time_minutes,
        "servings": servings,
        "calories": estimate_calories(ingredients, servings),
        "ingredients": dedupe_preserve_order([clean_text(item) for item in ingredients if len(clean_text(item)) >= 3]),
        "steps": steps,
        "tags": tags,
        "description": truncate(description, 180),
        "dietary": dietary,
    }


def normalise_wikibooks(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(raw.get("title", ""))
    if not title:
        return None

    ingredients_text = raw.get("ingredients_text") or raw.get("ingredients") or ""
    directions_text = raw.get("directions_text") or raw.get("directions") or raw.get("instructions") or ""
    ingredients = [clean_text(line) for line in str(ingredients_text).splitlines() if len(clean_text(line)) >= 3]
    steps = split_instructions(str(directions_text))
    if not ingredients and not steps:
        return None

    servings = estimate_servings(title, ingredients)
    first_step = truncate(steps[0], 80) if steps else "A delicious recipe."
    description = f"{title}. {first_step}"
    category = clean_text(raw.get("category", ""))
    return build_recipe(title, ingredients, steps, servings, description, [category] if category else None)


def normalise_themealdb(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(raw.get("strMeal", ""))
    if not title:
        return None

    ingredients: list[str] = []
    for index in range(1, 21):
        ingredient = clean_text(raw.get(f"strIngredient{index}", ""))
        measure = clean_text(raw.get(f"strMeasure{index}", ""))
        if ingredient:
            ingredients.append(f"{measure} {ingredient}".strip())

    if not ingredients:
        return None

    steps = split_instructions(str(raw.get("strInstructions", "")))
    area = clean_text(raw.get("strArea", ""))
    category = clean_text(raw.get("strCategory", ""))
    category_text = category.lower() if category else "recipe"
    description = f"A {area} {category_text} dish. {steps[0][:80] if steps else ''}".strip()
    return build_recipe(title, ingredients, steps, 4, description, [area, category])


def _drink_emoji(title: str, category: str, alcoholic: str) -> str:
    combined = f"{title} {category}".lower()
    for keywords, emoji in DRINK_EMOJI_MAP:
        if any(kw in combined for kw in keywords):
            return emoji
    return "🍹" if "alcoholic" in alcoholic.lower() else "🧃"


def normalise_cocktaildb(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(raw.get("strDrink", ""))
    if not title:
        return None

    ingredients: list[str] = []
    for index in range(1, 16):
        ingredient = clean_text(raw.get(f"strIngredient{index}", ""))
        measure = clean_text(raw.get(f"strMeasure{index}", ""))
        if ingredient:
            ingredients.append(f"{measure} {ingredient}".strip() if measure else ingredient)

    if not ingredients:
        return None

    instructions_raw = clean_text(raw.get("strInstructions", ""))
    steps = split_instructions(instructions_raw) or [f"Combine all ingredients and mix well. Serve {title}."]

    category = clean_text(raw.get("strCategory", "Cocktail"))
    alcoholic = clean_text(raw.get("strAlcoholic", "Alcoholic"))
    glass = clean_text(raw.get("strGlass", ""))

    is_alcoholic = "alcoholic" in alcoholic.lower() and alcoholic.lower() != "non alcoholic"
    drink_type = "cocktail" if is_alcoholic else "mocktail"
    description = f"A {alcoholic.lower()} {category.lower()}. Served in a {glass.lower()}. {steps[0][:80] if steps else ''}".strip()

    # Estimate calories for drinks (spirits ~65 kcal/oz, juice ~50 kcal/cup)
    calories = 180 if is_alcoholic else 90
    for ing in ingredients:
        low = ing.lower()
        if any(s in low for s in ["vodka", "rum", "gin", "whiskey", "tequila", "bourbon"]):
            calories += 40
        elif any(s in low for s in ["juice", "syrup", "sugar"]):
            calories += 20
        elif any(s in low for s in ["cream", "milk"]):
            calories += 30
    calories = min(calories, 600)

    extra_tags = [category, alcoholic, "Drink"]
    if glass:
        extra_tags.append(glass)
    if not is_alcoholic:
        extra_tags.append("Non-Alcoholic")
    else:
        extra_tags.append("Cocktail")

    dietary = [] if is_alcoholic else infer_dietary(ingredients)
    tags = infer_tags(title, ingredients, dietary)
    for tag in extra_tags:
        if tag and tag not in tags:
            tags.append(clean_text(tag))
    tags = dedupe_preserve_order(tags)

    return {
        "title": clean_text(title),
        "emoji": _drink_emoji(title, category, alcoholic),
        "time": 5,
        "servings": 1,
        "calories": calories,
        "ingredients": dedupe_preserve_order([clean_text(i) for i in ingredients if len(clean_text(i)) >= 2]),
        "steps": steps,
        "tags": tags,
        "description": truncate(description, 180),
        "dietary": dietary,
    }


def parse_epicurious_ingredients(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean_text(item) for item in value if len(clean_text(item)) >= 3]

    raw = str(value or "").strip()
    if not raw:
        return []

    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return [clean_text(item) for item in parsed if len(clean_text(item)) >= 3]
    except (ValueError, SyntaxError):
        print("Debug: Epicurious ingredient literal parse failed; falling back to comma split.")

    return [clean_text(item.strip(" []'\"")) for item in raw.split(",") if len(clean_text(item.strip(" []'\""))) >= 3]


def normalise_epicurious(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(raw.get("Title", "") or raw.get("title", ""))
    if not title:
        return None

    raw_ingredients = raw.get("Ingredients", "") or raw.get("ingredients", "")
    ingredients = parse_epicurious_ingredients(raw_ingredients)
    if not ingredients:
        return None

    instructions = str(raw.get("Instructions", "") or raw.get("instructions", ""))
    steps = split_instructions(instructions)
    servings = estimate_servings(title, ingredients)
    description = first_sentence(instructions) or f"{title} recipe."
    return build_recipe(title, ingredients, steps, servings, description)


def read_json_records(filepath: str) -> list[dict[str, Any]]:
    path = Path(filepath)
    content = path.read_text(encoding="utf-8", errors="replace")
    records: list[dict[str, Any]] = []

    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [record for record in parsed if isinstance(record, dict)]
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            parsed_line = json.loads(line)
        except json.JSONDecodeError:
            print(f"Warning: skipped invalid JSON line {line_number} in {filepath}")
            continue
        if isinstance(parsed_line, dict):
            records.append(parsed_line)
    return records


def load_wikibooks(filepath: str) -> list[dict[str, Any]]:
    records = read_json_records(filepath)
    recipes = [recipe for raw in records if (recipe := normalise_wikibooks(raw)) is not None]
    print(f"Wikibooks: loaded {len(records)} raw records, normalised {len(recipes)}")
    return recipes


async def get_json(client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        print(f"Warning: TheMealDB request failed for {url}: {exc}")
        return None
    if not isinstance(data, dict):
        return None
    return data


async def fetch_themealdb() -> list[dict[str, Any]]:
    recipes: list[dict[str, Any]] = []
    seen_meal_ids: set[str] = set()

    async with httpx.AsyncClient(timeout=10.0) as client:
        category_data = await get_json(client, f"{THEMEALDB_BASE_URL}/categories.php")
        categories = category_data.get("categories", []) if category_data else []
        if not isinstance(categories, list):
            return []

        for category in categories:
            if not isinstance(category, dict):
                continue
            category_name = clean_text(category.get("strCategory", ""))
            if not category_name:
                continue

            meals_data = await get_json(client, f"{THEMEALDB_BASE_URL}/filter.php", {"c": category_name})
            await asyncio.sleep(0.2)
            meals = meals_data.get("meals", []) if meals_data else []
            if not isinstance(meals, list):
                continue

            for meal in meals:
                if not isinstance(meal, dict):
                    continue
                meal_id = clean_text(meal.get("idMeal", ""))
                if not meal_id or meal_id in seen_meal_ids:
                    continue
                seen_meal_ids.add(meal_id)

                detail_data = await get_json(client, f"{THEMEALDB_BASE_URL}/lookup.php", {"i": meal_id})
                await asyncio.sleep(0.2)
                full_meals = detail_data.get("meals", []) if detail_data else []
                if not isinstance(full_meals, list) or not full_meals:
                    continue
                full_meal = full_meals[0]
                if isinstance(full_meal, dict) and (recipe := normalise_themealdb(full_meal)) is not None:
                    recipes.append(recipe)
                if len(seen_meal_ids) % 50 == 0:
                    print(f"TheMealDB: fetched {len(seen_meal_ids)}/~300...")

    print(f"TheMealDB: normalised {len(recipes)} recipes")
    return recipes


async def fetch_cocktaildb() -> list[dict[str, Any]]:
    """Fetch all cocktails + non-alcoholic drinks from TheCocktailDB."""
    recipes: list[dict[str, Any]] = []
    seen_drink_ids: set[str] = set()

    filters = [
        ("a", "Alcoholic"),
        ("a", "Non_Alcoholic"),
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for param_key, param_val in filters:
            list_data = await get_json(client, f"{COCKTAILDB_BASE_URL}/filter.php", {param_key: param_val})
            await asyncio.sleep(0.2)
            drinks = list_data.get("drinks", []) if list_data else []
            if not isinstance(drinks, list):
                continue

            print(f"CocktailDB ({param_val}): {len(drinks)} entries found")
            for drink in drinks:
                if not isinstance(drink, dict):
                    continue
                drink_id = clean_text(drink.get("idDrink", ""))
                if not drink_id or drink_id in seen_drink_ids:
                    continue
                seen_drink_ids.add(drink_id)

                detail_data = await get_json(client, f"{COCKTAILDB_BASE_URL}/lookup.php", {"i": drink_id})
                await asyncio.sleep(0.15)
                full_drinks = detail_data.get("drinks", []) if detail_data else []
                if not isinstance(full_drinks, list) or not full_drinks:
                    continue
                full_drink = full_drinks[0]
                if isinstance(full_drink, dict) and (recipe := normalise_cocktaildb(full_drink)) is not None:
                    recipes.append(recipe)
                if len(seen_drink_ids) % 100 == 0:
                    print(f"CocktailDB: fetched {len(seen_drink_ids)} drinks...")

    print(f"CocktailDB: normalised {len(recipes)} drinks")
    return recipes


def load_epicurious(filepath: str, limit: int | None = None) -> list[dict[str, Any]]:
    records = read_json_records(filepath)
    if limit is not None:
        records = records[: max(limit, 0)]

    recipes: list[dict[str, Any]] = []
    for index, raw in enumerate(records, 1):
        recipe = normalise_epicurious(raw)
        if recipe is not None:
            recipes.append(recipe)
        if index % 1000 == 0:
            print(f"Epicurious: processed {index} records, normalised {len(recipes)}")

    print(f"Epicurious: loaded {len(records)} raw records, normalised {len(recipes)}")
    return recipes


def title_key(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", title.lower())).strip()


def merge_and_deduplicate(sources: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    all_recipes = [recipe for source in sources for recipe in source]
    by_title: dict[str, dict[str, Any]] = {}
    for recipe in all_recipes:
        key = title_key(str(recipe.get("title", "")))
        if key:
            by_title[key] = recipe

    unique = list(by_title.values())
    for index, recipe in enumerate(unique, 1):
        recipe["id"] = f"{slugify(str(recipe['title']))}-{index:04d}"
    return unique


def validate_recipe(recipe: dict[str, Any]) -> bool:
    return (
        isinstance(recipe.get("title"), str)
        and bool(recipe["title"].strip())
        and isinstance(recipe.get("ingredients"), list)
        and len(recipe["ingredients"]) >= 1  # drinks may have just 2-3 items
        and isinstance(recipe.get("steps"), list)
        and len(recipe["steps"]) >= 1
        and isinstance(recipe.get("time"), int)
        and 1 <= recipe["time"] <= 480  # drinks = 5 min
        and isinstance(recipe.get("servings"), int)
        and 1 <= recipe["servings"] <= 20
        and isinstance(recipe.get("calories"), int)
        and 10 <= recipe["calories"] <= 2000  # low-cal drinks allowed
        and isinstance(recipe.get("emoji"), str)
        and bool(recipe["emoji"].strip())
    )


async def main() -> None:
    args = parse_args()

    print("\nRecipe Database Fetcher")
    print("━" * 42)

    all_sources: list[list[dict[str, Any]]] = []
    counts: dict[str, int] = {}

    if not args.skip_wikibooks:
        if Path(args.wikibooks_file).exists():
            wiki = load_wikibooks(args.wikibooks_file)
            all_sources.append(wiki)
            counts["Wikibooks"] = len(wiki)
        else:
            print(f"Warning: {args.wikibooks_file} not found — skipping Wikibooks.")
            print(
                "  To get it: python -c \"from datasets import load_dataset; "
                "ds = load_dataset('gossminn/wikibooks-cookbook'); "
                "ds['main'].to_json('wikibooks_recipes.json')\""
            )

    if not args.skip_themealdb:
        print("Fetching TheMealDB food recipes (~2 minutes due to rate limiting)...")
        mealdb = await fetch_themealdb()
        all_sources.append(mealdb)
        counts["TheMealDB"] = len(mealdb)

    if not args.skip_cocktaildb:
        print("Fetching TheCocktailDB drink recipes (~3 minutes due to rate limiting)...")
        cocktaildb = await fetch_cocktaildb()
        all_sources.append(cocktaildb)
        counts["CocktailDB"] = len(cocktaildb)

    if not args.skip_epicurious:
        if Path(args.epicurious_file).exists():
            epic = load_epicurious(args.epicurious_file, limit=args.epicurious_limit)
            all_sources.append(epic)
            counts["Epicurious"] = len(epic)
        else:
            print(f"Warning: {args.epicurious_file} not found — skipping Epicurious.")
            print("  To get it: git clone https://github.com/josephrmartinez/recipe-dataset epicurious_data")

    if not all_sources:
        print("Error: no sources loaded. Check your files and flags.")
        sys.exit(1)

    print("\nMerging sources and deduplicating...")
    final = merge_and_deduplicate(all_sources)
    before_validation = len(final)
    final = [recipe for recipe in final if validate_recipe(recipe)]
    dropped = before_validation - len(final)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        print(f"Warning: {args.output} already exists — overwriting.")
    output_path.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")

    total_loaded = sum(counts.values())
    print("\n" + "━" * 42)
    print("Sources loaded:")
    for source, count in counts.items():
        print(f"  {source:<20} {count:>6} recipes")
    print("━" * 42)
    print(f"  Total before dedup  {total_loaded:>6}")
    print(f"  Duplicates removed  {total_loaded - before_validation:>6}")
    print(f"  Failed validation   {dropped:>6}")
    print(f"  Final count         {len(final):>6}")
    print("━" * 42)
    print(f"\nSaved to: {output_path.resolve()}")
    print("\nNext step: python ingest.py")


if __name__ == "__main__":
    asyncio.run(main())
