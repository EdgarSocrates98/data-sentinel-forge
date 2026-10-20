import { Injectable, signal } from "@angular/core";

import type { ApiError } from "./api.models";

/**
 * Holds the most recent API failure so the shell can surface a
 * dismissible, screen-reader-announced toast. Errors are also
 * re-thrown by the interceptor so feature code can still react.
 */
@Injectable({ providedIn: "root" })
export class ApiErrorStore {
  private readonly _last = signal<ApiError | null>(null);
  readonly last = this._last.asReadonly();

  report(error: ApiError): void {
    this._last.set(error);
  }

  dismiss(): void {
    this._last.set(null);
  }
}
