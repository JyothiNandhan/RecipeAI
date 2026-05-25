import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private dark = new BehaviorSubject<boolean>(false);
  isDark$ = this.dark.asObservable();

  constructor() {
    const saved = localStorage.getItem('recipeai-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    this.apply(saved ? saved === 'dark' : prefersDark);
  }

  toggle(): void {
    this.apply(!this.dark.value);
  }

  get isDark(): boolean {
    return this.dark.value;
  }

  private apply(dark: boolean): void {
    this.dark.next(dark);
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    localStorage.setItem('recipeai-theme', dark ? 'dark' : 'light');
  }
}
