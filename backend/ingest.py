"""
Run this once before starting the server:
    python ingest.py

This loads recipes.json into ChromaDB with sentence-transformer embeddings.
Safe to re-run because it clears and rebuilds the collection each time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = str(BASE_DIR / "chroma_db")
COLLECTION_NAME = "recipes"
MODEL_NAME = "all-MiniLM-L6-v2"
RECIPES_FILE = BASE_DIR / "recipes.json"


def build_recipe_text(recipe: dict[str, Any]) -> str:
    """Convert a recipe dict into the searchable text that gets embedded."""
    return (
        f"{recipe['title']} "
        f"{' '.join(recipe['tags'])} "
        f"{' '.join(recipe['ingredients'])} "
        f"{recipe['description']}"
    )


def main() -> None:
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Connecting to ChromaDB at: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print("Deleted existing collection.")
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)
    print("Created new collection.")

    with RECIPES_FILE.open(encoding="utf-8") as file:
        recipes: list[dict[str, Any]] = json.load(file)

    print(f"Embedding {len(recipes)} recipes...")
    for recipe in recipes:
        text = build_recipe_text(recipe)
        embedding = model.encode(text).tolist()
        collection.add(
            ids=[recipe["id"]],
            embeddings=[embedding],
            documents=[text],
            metadatas=[
                {
                    "title": recipe["title"],
                    "emoji": recipe["emoji"],
                    "time": recipe["time"],
                    "servings": recipe["servings"],
                    "calories": recipe["calories"],
                    "ingredients": json.dumps(recipe["ingredients"]),
                    "steps": json.dumps(recipe["steps"]),
                    "tags": json.dumps(recipe["tags"]),
                    "description": recipe["description"],
                    "dietary": json.dumps(recipe.get("dietary", [])),
                }
            ],
        )
        print(f"  Ingested: {recipe['title']}")

    print(f"\nDone. {len(recipes)} recipes stored in ChromaDB.")


if __name__ == "__main__":
    main()

