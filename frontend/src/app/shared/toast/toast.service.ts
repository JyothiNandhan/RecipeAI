import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toastsSubject = new BehaviorSubject<Toast[]>([]);
  public toasts$ = this.toastsSubject.asObservable();
  private readonly maxToasts = 4;
  private readonly durationMs = 4000;

  success(message: string): void {
    this.show(message, 'success');
  }

  error(message: string): void {
    this.show(message, 'error');
  }

  info(message: string): void {
    this.show(message, 'info');
  }

  warning(message: string): void {
    this.show(message, 'warning');
  }

  remove(id: string): void {
    const currentToasts = this.toastsSubject.value;
    this.toastsSubject.next(currentToasts.filter(t => t.id !== id));
  }

  private show(message: string, type: ToastType): void {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = { id, message, type };
    
    let currentToasts = [...this.toastsSubject.value, newToast];
    
    // Enforce maximum of 4 toasts
    if (currentToasts.length > this.maxToasts) {
      currentToasts = currentToasts.slice(currentToasts.length - this.maxToasts);
    }
    
    this.toastsSubject.next(currentToasts);

    // Auto dismiss
    setTimeout(() => {
      this.remove(id);
    }, this.durationMs);
  }
}
