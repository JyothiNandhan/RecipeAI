import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { LoginRequest, RegisterRequest, TokenResponse, UserOut } from '../models/auth.model';

import { environment } from '../../environments/environment';

const API = environment.apiUrl;
const ACCESS_KEY = 'recipeai_access';
const REFRESH_KEY = 'recipeai_refresh';
const USER_KEY = 'recipeai_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private userSubject = new BehaviorSubject<UserOut | null>(this.loadUser());
  currentUser$ = this.userSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  get isLoggedIn(): boolean {
    return !!this.getAccessToken();
  }

  get isAdmin(): boolean {
    return this.userSubject.value?.role === 'admin';
  }

  get currentUser(): UserOut | null {
    return this.userSubject.value;
  }

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  login(payload: LoginRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${API}/auth/login`, payload).pipe(
      tap(res => this.saveSession(res)),
      catchError(this.handleError)
    );
  }

  register(payload: RegisterRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${API}/auth/register`, payload).pipe(
      tap(res => this.saveSession(res)),
      catchError(this.handleError)
    );
  }

  refresh(): Observable<TokenResponse> {
    const refresh_token = localStorage.getItem(REFRESH_KEY);
    if (!refresh_token) return throwError(() => new Error('No refresh token'));
    return this.http.post<TokenResponse>(`${API}/auth/refresh`, { refresh_token }).pipe(
      tap(res => this.saveSession(res)),
      catchError(() => {
        this.logout();
        return throwError(() => new Error('Session expired'));
      })
    );
  }

  logout(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    this.userSubject.next(null);
    this.router.navigate(['/login']);
  }

  private saveSession(res: TokenResponse): void {
    localStorage.setItem(ACCESS_KEY, res.access_token);
    localStorage.setItem(REFRESH_KEY, res.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    this.userSubject.next(res.user);
  }

  private loadUser(): UserOut | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    const detail = (error.error as { detail?: string })?.detail;
    return throwError(() => new Error(detail || 'Authentication failed. Please try again.'));
  }
}
