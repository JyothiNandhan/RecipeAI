import { Component } from '@angular/core';
import { Recipe } from '../../models/recipe.model';
import { EnvironmentContextService } from '../../services/environment-context.service';
import { RecipeService } from '../../services/recipe.service';
import { TokenService } from '../../services/token.service';

interface DietaryGoal {
  label: string;
  icon: string;
  desc: string;
}

@Component({
  selector: 'app-preferences',
  templateUrl: './preferences.component.html',
  styleUrls: ['./preferences.component.scss'],
})
export class PreferencesComponent {
  dietaryGoals: DietaryGoal[] = [
    { label: 'Vegetarian', icon: '🍃', desc: 'Plant-based meals' },
    { label: 'Vegan', icon: '🌱', desc: 'No animal products' },
    { label: 'Gluten-free', icon: '🛡', desc: 'No wheat or gluten' },
    { label: 'High protein', icon: '🏋', desc: 'Muscle-building meals' },
    { label: 'Low carb', icon: '🔥', desc: 'Keto-friendly options' },
    { label: 'Whole foods', icon: '🍎', desc: 'Minimally processed' },
    { label: 'Dairy-free', icon: '💧', desc: 'No dairy products' },
    { label: 'Quick meals', icon: '◷', desc: 'Ready in under 20 min' },
  ];

  selectedGoal: string | null = null;
  maxTime = 30;
  servings = 2;
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

  selectGoal(goal: string): void {
    this.selectedGoal = goal;
  }

  findRecipes(): void {
    if (!this.selectedGoal) {
      this.error = 'Choose one preference first.';
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
        mode: 'preferences',
        navigator_token: this.tokenService.getToken(),
        dietary_goal: this.selectedGoal,
        max_time: this.maxTime,
        servings: this.servings,
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
