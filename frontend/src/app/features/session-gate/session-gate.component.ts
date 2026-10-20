import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { ActivatedRoute, Router } from "@angular/router";

import { TranslatePipe } from "../../core/i18n/translate.pipe";
import { SessionService } from "../../core/session/session.service";

type GateState = "idle" | "connecting" | "invalid" | "required";

/**
 * Session onboarding gate (ds-0101 / ADR-0014). The only screen a clean
 * browser sees before the dashboard: collect a bearer token, validate it
 * against a real endpoint via `SessionService.establish()`, and route to
 * the originally requested page (or the dashboard) on success. Never
 * silently retries on expiry — the expired state is explicit.
 */
@Component({
  selector: "ds-session-gate",
  standalone: true,
  imports: [FormsModule, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./session-gate.component.html",
  styleUrl: "./session-gate.component.css",
})
export class SessionGateComponent {
  private readonly session = inject(SessionService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly tokenInput = signal("");
  protected readonly state = signal<GateState>("idle");
  protected readonly wasExpired = this.session.isExpired;

  protected connect(): void {
    const token = this.tokenInput().trim();
    if (!token) {
      this.state.set("required");
      return;
    }
    this.state.set("connecting");
    this.session.establish(token).subscribe((ok) => {
      if (ok) {
        this.session.acknowledgeExpiry();
        const redirect =
          this.route.snapshot.queryParamMap.get("redirect") ?? "/";
        // In-app navigation only — a redirect param must stay a local
        // path (review).
        void this.router.navigateByUrl(
          redirect.startsWith("/") ? redirect : "/",
        );
      } else {
        this.state.set("invalid");
      }
    });
  }
}
