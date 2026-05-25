import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { DailyComponent } from './pages/daily/daily.component';
import { IngredientsComponent } from './pages/ingredients/ingredients.component';
import { PreferencesComponent } from './pages/preferences/preferences.component';
import { authGuard, adminGuard } from './core/guards/auth.guard';

const routes: Routes = [
  { path: '', redirectTo: 'ingredients', pathMatch: 'full' },

  // Public
  { path: 'login',    loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'register', loadComponent: () => import('./pages/register/register.component').then(m => m.RegisterComponent) },

  // Protected - require login
  { path: 'ingredients', component: IngredientsComponent, canActivate: [authGuard] },
  { path: 'preferences', component: PreferencesComponent, canActivate: [authGuard] },
  { path: 'daily',       component: DailyComponent,       canActivate: [authGuard] },

  // Admin protected
  { path: 'admin/observability', redirectTo: '/admin/observability', pathMatch: 'full' },

  // Error pages
  { path: 'unauthorized', loadComponent: () => import('./pages/unauthorized/unauthorized.component').then(m => m.UnauthorizedComponent) },
  { path: '**',           loadComponent: () => import('./pages/not-found/not-found.component').then(m => m.NotFoundComponent) },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
