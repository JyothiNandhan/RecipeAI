import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

const SESSION_KEY = 'recipeai_navigator_token';

@Injectable({ providedIn: 'root' })
export class TokenService {
  private token = sessionStorage.getItem(SESSION_KEY) || '';
  private readonly invalidSubject = new BehaviorSubject<boolean>(false);

  readonly invalid$: Observable<boolean> = this.invalidSubject.asObservable();

  setToken(token: string): void {
    this.token = token.trim();
    sessionStorage.setItem(SESSION_KEY, this.token);
    this.invalidSubject.next(false);
  }

  getToken(): string {
    return this.token;
  }

  hasToken(): boolean {
    return this.token.length > 0;
  }

  clearToken(): void {
    this.token = '';
    sessionStorage.removeItem(SESSION_KEY);
    this.invalidSubject.next(false);
  }

  markInvalid(): void {
    this.invalidSubject.next(true);
  }
}

