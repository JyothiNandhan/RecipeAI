import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="error-page">
      <div class="error-code">404</div>
      <h1 class="error-title">Page not found</h1>
      <p class="error-message">The link you followed may be broken, or the page may have been removed.</p>
      <a routerLink="/ingredients" class="btn-primary-link">Back to App →</a>
    </div>
  `,
  styles: [`
    .error-page {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      min-height: calc(100vh - 64px);
      padding: var(--space-8) var(--space-4);
      gap: var(--space-4);
    }
    .error-code {
      font-size: 6rem;
      font-weight: 800;
      line-height: 1;
      background: linear-gradient(135deg, var(--accent), #A78BFA);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .error-title { font-size: var(--text-3xl); font-weight: 800; color: var(--text-primary); }
    .error-message { color: var(--text-secondary); max-width: 400px; }
    .btn-primary-link {
      margin-top: var(--space-4);
      padding: var(--space-3) var(--space-6);
      background: linear-gradient(135deg, var(--accent), #7C3AED);
      color: #fff;
      border-radius: var(--radius-md);
      font-weight: 600;
      text-decoration: none;
      transition: filter 120ms;
    }
    .btn-primary-link:hover { filter: brightness(1.08); color: #fff; }
  `]
})
export class NotFoundComponent {}
