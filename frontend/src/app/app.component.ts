import { Component, OnInit } from '@angular/core';
import { ThemeService } from './services/theme.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  constructor(private theme: ThemeService) {}

  // ThemeService constructor already applies saved theme on boot.
  // This ensures it runs when the app initializes.
  ngOnInit(): void {}
}
