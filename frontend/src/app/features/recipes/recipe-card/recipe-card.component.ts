import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Recipe } from '../../../models/recipe.model';

@Component({
  selector: 'app-recipe-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './recipe-card.component.html',
  styleUrls: ['./recipe-card.component.scss']
})
export class RecipeCardComponent {
  @Input({ required: true }) recipe!: Recipe;
  expanded = false;

  get title(): string {
    return this.recipe.name || this.recipe.title || 'Unknown Recipe';
  }

  get matchExplanation(): string {
    return this.recipe.match_explanation || this.recipe.match_reason || '';
  }

  get time(): number {
    return this.recipe.prep_time_minutes || this.recipe.time || 0;
  }

  get steps(): string[] {
    return this.recipe.instructions || this.recipe.steps || [];
  }
}
