import { Injectable } from '@angular/core';
import { Observable, of, delay } from 'rxjs';
import { mockRecipes } from './mock-data';
import { Recipe } from '../../models/recipe.model';

@Injectable({
  providedIn: 'root'
})
export class MockApiService {
  getRecommendations(): Observable<{ recipes: Recipe[], mode: string, retrieved_count: number }> {
    const count = Math.floor(Math.random() * 4) + 3; // 3 to 6
    const shuffled = [...mockRecipes].sort(() => 0.5 - Math.random());
    const selected = shuffled.slice(0, count);
    
    return of({
      recipes: selected,
      mode: 'mock',
      retrieved_count: count
    }).pipe(delay(Math.floor(Math.random() * 400) + 800)); // 800-1200ms delay
  }

  getWeatherContext(): Observable<any> {
    return of({
      temperature: 72,
      condition: "Sunny",
      location: "Mock City"
    }).pipe(delay(500));
  }
}
