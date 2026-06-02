import { Injectable } from '@angular/core';
import {
  HttpRequest, HttpHandler, HttpEvent, HttpInterceptor, HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private refreshing = false;
  private refreshSubject = new BehaviorSubject<string | null>(null);

  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const headers: Record<string, string> = this.ngrokHeaders(req);

    // Skip auth endpoints
    if (req.url.includes('/auth/')) {
      return next.handle(this.withHeaders(req, headers));
    }

    const token = this.auth.getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const authReq = this.withHeaders(req, headers);

    return next.handle(authReq).pipe(
      catchError((err: HttpErrorResponse) => {
        if (err.status === 401 && !req.url.includes('/auth/refresh')) {
          return this.handle401(req, next);
        }
        return throwError(() => err);
      })
    );
  }

  private handle401(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    if (this.refreshing) {
      return this.refreshSubject.pipe(
        filter(t => t !== null),
        take(1),
        switchMap(token => next.handle(this.withHeaders(req, {
          ...this.ngrokHeaders(req),
          Authorization: `Bearer ${token}`,
        })))
      );
    }

    this.refreshing = true;
    this.refreshSubject.next(null);

    return this.auth.refresh().pipe(
      switchMap(res => {
        this.refreshing = false;
        this.refreshSubject.next(res.access_token);
        return next.handle(this.withHeaders(req, {
          ...this.ngrokHeaders(req),
          Authorization: `Bearer ${res.access_token}`,
        }));
      }),
      catchError(err => {
        this.refreshing = false;
        this.auth.logout();
        return throwError(() => err);
      })
    );
  }

  private ngrokHeaders(req: HttpRequest<unknown>): Record<string, string> {
    return req.url.includes('.ngrok-free.')
      ? { 'ngrok-skip-browser-warning': 'true' }
      : {};
  }

  private withHeaders(
    req: HttpRequest<unknown>,
    headers: Record<string, string>,
  ): HttpRequest<unknown> {
    return Object.keys(headers).length ? req.clone({ setHeaders: headers }) : req;
  }
}
