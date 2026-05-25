import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { RecipeRequest, RecipeResponse } from '../models/recipe.model';
import { TokenService } from './token.service';

import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class RecipeService {
  private readonly apiUrl = environment.apiUrl;

  constructor(
    private readonly http: HttpClient,
    private readonly tokenService: TokenService,
  ) {}

  getRecommendations(request: RecipeRequest): Observable<RecipeResponse> {
    return this.http
      .post<RecipeResponse>(`${this.apiUrl}/recommend`, request)
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  checkHealth(): Observable<Record<string, string>> {
    return this.http
      .get<Record<string, string>>(`${this.apiUrl}/health`)
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let message = 'An unexpected error occurred.';

    if (error.status === 0) {
      message = 'Cannot reach the backend. Make sure FastAPI is running on port 8000.';
    } else if (error.status === 400) {
      message = this.detail(error) || 'Invalid request.';
    } else if (error.status === 401) {
      this.tokenService.markInvalid();
      message = 'Invalid NaviGator API token. Please check your token and try again.';
    } else if (error.status === 404) {
      message = 'No recipes found. The database may need to be ingested. Run ingest.py.';
    } else if (error.status === 429) {
      message = 'NaviGator rate limit reached. Please wait a moment.';
    } else if (error.status === 504) {
      message = 'NaviGator took too long to respond. Please try again.';
    } else if (error.status >= 500) {
      message = this.detail(error) || 'Server error. Please try again.';
    }

    return throwError(() => new Error(message));
  }

  private detail(error: HttpErrorResponse): string | null {
    const detail = (error.error as { detail?: unknown } | null)?.detail;
    return typeof detail === 'string' ? detail : null;
  }
}

