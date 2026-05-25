import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpResponse
} from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { MockApiService } from '../mock/mock-api.service';

@Injectable()
export class MockApiInterceptor implements HttpInterceptor {
  constructor(private mockApiService: MockApiService) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    if (environment.useMockApi) {
      if (request.url.includes('/recommend')) {
        return this.mockApiService.getRecommendations().pipe(
          switchMap(mockResponse => of(new HttpResponse({ status: 200, body: mockResponse })))
        );
      }
      if (request.url.includes('/weather')) {
         return this.mockApiService.getWeatherContext().pipe(
          switchMap(mockResponse => of(new HttpResponse({ status: 200, body: mockResponse })))
        );
      }
    }
    return next.handle(request);
  }
}
