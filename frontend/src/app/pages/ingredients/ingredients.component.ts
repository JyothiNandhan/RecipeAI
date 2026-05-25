import { Component } from '@angular/core';
import { Recipe } from '../../models/recipe.model';
import { EnvironmentContextService } from '../../services/environment-context.service';
import { RecipeService } from '../../services/recipe.service';
import { TokenService } from '../../services/token.service';

@Component({
  selector: 'app-ingredients',
  templateUrl: './ingredients.component.html',
  styleUrls: ['./ingredients.component.scss'],
})
export class IngredientsComponent {
  commonIngredients: string[] = [
    'eggs',
    'chicken',
    'pasta',
    'rice',
    'tomatoes',
    'garlic',
    'onion',
    'spinach',
    'cheese',
    'lemon',
    'potatoes',
    'mushrooms',
    'salmon',
    'beans',
    'avocado',
    'broccoli',
    'butter',
    'flour',
    'olive oil',
    'yogurt',
    'ginger',
    'bell peppers',
    'sweet potato',
    'chickpeas',
  ];

  selectedIngredients: Set<string> = new Set<string>();
  customIngredients: string[] = [];
  customInput = '';
  recipes: Recipe[] = [];
  loading = false;
  error: string | null = null;
  retrievedCount = 0;
  hasSearched = false;

  constructor(
    private readonly environmentContext: EnvironmentContextService,
    private readonly recipeService: RecipeService,
    public readonly tokenService: TokenService,
  ) {}

  toggleIngredient(ingredient: string): void {
    if (this.selectedIngredients.has(ingredient)) {
      this.selectedIngredients.delete(ingredient);
    } else {
      this.selectedIngredients.add(ingredient);
    }
  }

  addCustom(): void {
    const ingredient = this.customInput.trim().toLowerCase();
    if (!ingredient || this.selectedIngredients.has(ingredient)) {
      this.customInput = '';
      return;
    }

    this.customIngredients.push(ingredient);
    this.selectedIngredients.add(ingredient);
    this.customInput = '';
  }

  removeCustom(ingredient: string): void {
    this.customIngredients = this.customIngredients.filter((item: string) => item !== ingredient);
    this.selectedIngredients.delete(ingredient);
  }

  findRecipes(): void {
    const ingredients = Array.from(this.selectedIngredients);
    if (ingredients.length === 0) {
      this.error = 'Select at least one ingredient.';
      return;
    }

    if (!this.tokenService.hasToken()) {
      this.error = 'Add your NaviGator token first.';
      return;
    }

    this.loading = true;
    this.error = null;
    this.recipes = [];
    this.retrievedCount = 0;
    this.hasSearched = true;

    this.recipeService
      .getRecommendations({
        mode: 'ingredients',
        navigator_token: this.tokenService.getToken(),
        ingredients,
        location_name: this.environmentContext.getLocationName(),
      })
      .subscribe({
        next: (response) => {
          this.recipes = response.recipes;
          this.retrievedCount = response.retrieved_count;
          this.loading = false;
        },
        error: (error: Error) => {
          this.error = error.message;
          this.loading = false;
        },
      });
  }
}
