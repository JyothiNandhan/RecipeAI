import { Component, OnInit } from '@angular/core';
import { Recipe } from '../../models/recipe.model';
import { EnvironmentContextService } from '../../services/environment-context.service';
import { RecipeService } from '../../services/recipe.service';
import { TokenService } from '../../services/token.service';

@Component({
  selector: 'app-daily',
  templateUrl: './daily.component.html',
  styleUrls: ['./daily.component.scss'],
})
export class DailyComponent implements OnInit {
  recipe: Recipe | null = null;
  loading = false;
  error: string | null = null;
  hasToken = false;
  hasSearched = false;

  constructor(
    private readonly environmentContext: EnvironmentContextService,
    private readonly recipeService: RecipeService,
    private readonly tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.hasToken = this.tokenService.hasToken();
    if (this.hasToken) {
      this.getDaily();
    }
  }

  getDaily(): void {
    if (!this.tokenService.hasToken()) {
      this.hasToken = false;
      this.error = null;
      this.recipe = null;
      return;
    }

    this.hasToken = true;
    this.loading = true;
    this.error = null;
    this.recipe = null;
    this.hasSearched = true;

    this.recipeService
      .getRecommendations({
        mode: 'daily',
        navigator_token: this.tokenService.getToken(),
        location_name: this.environmentContext.getLocationName(),
      })
      .subscribe({
        next: (response) => {
          this.recipe = response.recipes[0] ?? null;
          this.loading = false;
        },
        error: (error: Error) => {
          this.error = error.message;
          this.loading = false;
        },
      });
  }
}
