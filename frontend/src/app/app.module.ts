import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { TokenInputComponent } from './components/token-input/token-input.component';
import { IngredientsComponent } from './pages/ingredients/ingredients.component';
import { PreferencesComponent } from './pages/preferences/preferences.component';
import { DailyComponent } from './pages/daily/daily.component';

import { NavbarComponent } from './shared/navbar/navbar.component';
import { ToastContainerComponent } from './shared/toast/toast-container.component';
import { SkeletonComponent } from './shared/skeleton/skeleton.component';
import { ErrorBannerComponent } from './shared/error-banner/error-banner.component';
import { EmptyStateComponent } from './shared/empty-state/empty-state.component';
import { RecipeCardComponent } from './features/recipes/recipe-card/recipe-card.component';

import { AuthInterceptor } from './core/interceptors/auth.interceptor';
import { MockApiInterceptor } from './core/interceptors/mock-api.interceptor';

@NgModule({
  declarations: [
    AppComponent,
    TokenInputComponent,
    IngredientsComponent,
    PreferencesComponent,
    DailyComponent,
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule,
    AppRoutingModule,
    NavbarComponent,
    ToastContainerComponent,
    SkeletonComponent,
    ErrorBannerComponent,
    EmptyStateComponent,
    RecipeCardComponent,
  ],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor,    multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: MockApiInterceptor, multi: true },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
