import {
  HttpErrorResponse,
  HttpInterceptorFn,
} from "@angular/common/http";
import { inject } from "@angular/core";
import { catchError, throwError } from "rxjs";

import { ApiErrorStore } from "./api-error.store";
import type { ApiError } from "./api.models";

/**
 * Normalizes HTTP failures into `ApiError`, records them in the
 * `ApiErrorStore` (shell toast), and re-throws so callers keep control.
 */
export const httpErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(ApiErrorStore);

  return next(req).pipe(
    catchError((err: unknown) => {
      const apiError = normalizeError(err, req.url);
      store.report(apiError);
      return throwError(() => apiError);
    }),
  );
};

function normalizeError(err: unknown, url: string): ApiError {
  if (err instanceof HttpErrorResponse) {
    const detail = extractDetail(err.error);
    let message: string;
    if (err.status === 0) {
      // Network failure / API offline / CORS rejection.
      message = "api.error.unreachable";
    } else if (err.status >= 500) {
      message = "api.error.server";
    } else if (err.status === 404) {
      message = "api.error.notFound";
    } else {
      message = "api.error.request";
    }
    return { status: err.status, message, detail, url };
  }
  return { status: 0, message: "api.error.unknown", detail: null, url };
}

function extractDetail(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      // FastAPI validation errors: [{loc, msg, type}, ...]
      return d
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item),
        )
        .join("; ");
    }
    return String(d);
  }
  return null;
}
