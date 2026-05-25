import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';
import { EnvironmentContextService } from '../../services/environment-context.service';
import { TokenService } from '../../services/token.service';

@Component({
  selector: 'app-token-input',
  templateUrl: './token-input.component.html',
  styleUrls: ['./token-input.component.scss'],
})
export class TokenInputComponent implements OnInit, OnDestroy {
  tokenInput = '';
  saved = false;
  visible = false;
  invalid = false;
  locationInput = '';
  private subscription?: Subscription;

  constructor(
    private readonly tokenService: TokenService,
    private readonly environmentContext: EnvironmentContextService,
  ) {}

  ngOnInit(): void {
    this.saved = this.tokenService.hasToken();
    this.locationInput = this.environmentContext.getLocationName();
    this.subscription = this.tokenService.invalid$.subscribe((invalid: boolean) => {
      this.invalid = invalid;
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  save(): void {
    if (this.tokenInput.trim().length < 10) {
      this.invalid = true;
      return;
    }

    this.tokenService.setToken(this.tokenInput.trim());
    this.saved = true;
    this.invalid = false;
    this.tokenInput = '';
  }

  clear(): void {
    this.tokenService.clearToken();
    this.saved = false;
    this.invalid = false;
    this.tokenInput = '';
  }

  toggleVisibility(): void {
    this.visible = !this.visible;
  }

  saveLocation(): void {
    this.environmentContext.setLocationName(this.locationInput);
    this.locationInput = this.environmentContext.getLocationName();
  }
}
