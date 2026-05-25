import { Component, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { ThemeService } from '../../services/theme.service';
import { TokenService } from '../../services/token.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss']
})
export class NavbarComponent implements OnInit {
  isMockMode = environment.useMockApi;
  isMenuOpen = false;
  isUserMenuOpen = false;
  isTokenPopoverOpen = false;
  isDark = false;
  tokenInput = '';

  constructor(
    public auth: AuthService,
    public theme: ThemeService,
    public tokenService: TokenService
  ) {}

  ngOnInit(): void {
    this.theme.isDark$.subscribe(dark => this.isDark = dark);
    this.tokenInput = this.tokenService.getToken();
  }

  toggleMenu(): void { this.isMenuOpen = !this.isMenuOpen; }
  toggleUserMenu(): void { this.isUserMenuOpen = !this.isUserMenuOpen; this.isTokenPopoverOpen = false; }
  toggleTokenPopover(): void { this.isTokenPopoverOpen = !this.isTokenPopoverOpen; this.isUserMenuOpen = false; }
  toggleTheme(): void { this.theme.toggle(); }

  saveToken(): void {
    if (this.tokenInput.trim()) {
      this.tokenService.setToken(this.tokenInput.trim());
    }
    this.isTokenPopoverOpen = false;
  }

  clearToken(): void {
    this.tokenInput = '';
    this.tokenService.clearToken();
    this.isTokenPopoverOpen = false;
  }

  logout(): void {
    this.isUserMenuOpen = false;
    this.auth.logout();
  }

  get userInitial(): string {
    return (this.auth.currentUser?.email?.[0] ?? '?').toUpperCase();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.isMenuOpen = false;
    this.isUserMenuOpen = false;
    this.isTokenPopoverOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocClick(e: Event): void {
    const t = e.target as HTMLElement;
    if (!t.closest('.user-menu-wrapper')) this.isUserMenuOpen = false;
    if (!t.closest('.token-wrapper')) this.isTokenPopoverOpen = false;
  }
}
