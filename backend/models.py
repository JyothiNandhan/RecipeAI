from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Auth models ────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str = Field(min_length=5)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserOut


# ── Recipe models ──────────────────────────────────────────────────────────────

class RecipeRequest(BaseModel):
    mode: Literal["ingredients", "preferences", "daily"]
    navigator_token: str = Field(min_length=1)
    ingredients: list[str] | None = None
    dietary_goal: str | None = None
    max_time: int | None = None
    servings: int | None = None
    location_name: str | None = None


class Recipe(BaseModel):
    title: str
    emoji: str
    time: int
    servings: int
    calories: int
    ingredients: list[str]
    steps: list[str]
    tags: list[str]
    description: str
    match_reason: str
    dish_story: str | None = None
    flavor_profile: str | None = None
    key_technique: str | None = None
    pro_tips: list[str] | None = None
    ingredient_insights: str | None = None
    serving_suggestion: str | None = None
    estimated_difficulty: str | None = None
    estimated_time_breakdown: dict[str, int] | None = None


class RecipeResponse(BaseModel):
    recipes: list[Recipe]
    mode: str
    retrieved_count: int
