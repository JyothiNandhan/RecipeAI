export interface RecipeRequest {
  mode: 'ingredients' | 'preferences' | 'daily';
  navigator_token: string;
  ingredients?: string[];
  dietary_goal?: string;
  max_time?: number;
  servings?: number;
  location_name?: string;
}

export interface Recipe {
  id?: string;
  title?: string;
  name?: string; // Phase 2 Mock
  emoji?: string;
  time?: number;
  prep_time_minutes?: number; // Phase 2 Mock
  servings?: number;
  calories: number;
  cuisine?: string; // Phase 2 Mock
  meal_type?: string; // Phase 2 Mock
  ingredients: string[];
  steps?: string[];
  instructions?: string[]; // Phase 2 Mock
  tags?: string[];
  description?: string;
  match_reason?: string;
  match_explanation?: string; // Phase 2 Mock
  matched_ingredients?: string[]; // Phase 2 Mock
  missing_ingredients?: string[]; // Phase 2 Mock
  match_score?: number; // Phase 2 Mock
  weather_context?: string; // Phase 2 Mock
  time_context?: string; // Phase 2 Mock
  dish_story?: string;
  flavor_profile?: string;
  key_technique?: string;
  pro_tips?: string[];
  ingredient_insights?: string;
  serving_suggestion?: string;
  estimated_difficulty?: string;
  estimated_time_breakdown?: {
    prep_minutes: number;
    cook_minutes: number;
  };
}

export interface RecipeResponse {
  recipes: Recipe[];
  mode: string;
  retrieved_count: number;
}
