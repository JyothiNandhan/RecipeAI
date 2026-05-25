import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class EnvironmentContextService {
  private locationName = 'Gainesville, FL';

  setLocationName(locationName: string): void {
    this.locationName = locationName.trim();
  }

  getLocationName(): string {
    return this.locationName;
  }

  hasLocationName(): boolean {
    return this.locationName.length > 0;
  }
}
