import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  email = '';
  password = '';
  confirmPassword = '';
  loading = false;
  error: string | null = null;
  showPassword = false;

  constructor(private auth: AuthService, private router: Router) {}

  submit(): void {
    if (!this.email || !this.password) { this.error = 'Please fill in all fields.'; return; }
    if (this.password !== this.confirmPassword) { this.error = 'Passwords do not match.'; return; }
    if (this.password.length < 8) { this.error = 'Password must be at least 8 characters.'; return; }
    this.loading = true;
    this.error = null;
    this.auth.register({ email: this.email, password: this.password }).subscribe({
      next: () => this.router.navigate(['/ingredients']),
      error: (e: Error) => { this.error = e.message; this.loading = false; }
    });
  }
}
