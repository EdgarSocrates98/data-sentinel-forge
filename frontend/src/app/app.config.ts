import {
  provideHttpClient,
  withInterceptors,
} from "@angular/common/http";
import { ApplicationConfig, provideZoneChangeDetection } from "@angular/core";
import { provideRouter, TitleStrategy, withInMemoryScrolling } from "@angular/router";

import { routes } from "./app.routes";
import { httpErrorInterceptor } from "./core/http-error.interceptor";
import { LocalizedTitleStrategy } from "./core/i18n/localized-title.strategy";
import { authInterceptor } from "./core/session/auth.interceptor";

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      routes,
      withInMemoryScrolling({ scrollPositionRestoration: "top" }),
    ),
    // authInterceptor must run before httpErrorInterceptor so a 401 is
    // already handled (session cleared + routed to the gate) by the time
    // the generic error toast would otherwise fire.
    provideHttpClient(
      withInterceptors([authInterceptor, httpErrorInterceptor]),
    ),
    // useExisting: a single instance shared by the Router (TitleStrategy
    // token) and AppComponent's locale-refresh effect. With useClass the
    // component would inject a *different* root instance whose
    // lastSnapshot is never set, leaving <title> stale on locale change.
    { provide: TitleStrategy, useExisting: LocalizedTitleStrategy },
  ],
};
