import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './skeleton.component.html',
  styleUrls: ['./skeleton.component.scss']
})
export class SkeletonComponent {
  @Input() type: 'card' | 'text' | 'title' | 'avatar' = 'text';
  @Input() count: number = 1;

  get countArray(): number[] {
    return new Array(this.count);
  }
}
