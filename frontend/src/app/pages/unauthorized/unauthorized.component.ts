import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="error-page">
      <span class="error-icon" aria-hidden="true">🔒</span>
      <h1 class="error-title">Access Denied</h1>
      <p class="error-message">You don't have permission to view this page.</p>
      <a routerLink="/ingredients" class="btn-primary-link">Go to App →</a>
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
    .error-icon { font-size: 4rem; }
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
export class UnauthorizedComponent {}
