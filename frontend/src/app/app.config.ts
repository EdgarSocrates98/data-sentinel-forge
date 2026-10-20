import {
  provideHttpClient,
  withInterceptors,
} from "@angular/common/http";
import { ApplicationConfig, provideZoneChangeDetection } from "@angular/core";
import { provideRouter, TitleStrategy, withInMemoryScrolling } from "@angular/router";

import { routes } from "./app.routes";
import { httpErrorInterceptor } from "./core/http-error.interceptor";
import { LocalizedTitleStrategy } from "./core/i18n/localized-title.strategy";

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      routes,
      withInMemoryScrolling({ scrollPositionRestoration: "top" }),
    ),
    provideHttpClient(withInterceptors([httpErrorInterceptor])),
    { provide: TitleStrategy, useClass: LocalizedTitleStrategy },
  ],
};
