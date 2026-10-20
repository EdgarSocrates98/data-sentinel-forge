import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";

import { AppComponent } from "./app.component";
import { routes } from "./app.routes";

describe("AppComponent (shell)", () => {
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter(routes),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
  });

  it("renders the app shell with landmarks", () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector("header.topbar")).toBeTruthy();
    expect(el.querySelector("nav.sidenav")).toBeTruthy();
    expect(el.querySelector("main#main-content")).toBeTruthy();
  });

  it("renders a skip link targeting main content", () => {
    const el: HTMLElement = fixture.nativeElement;
    const skip = el.querySelector<HTMLAnchorElement>("a.skip-link");
    expect(skip).toBeTruthy();
    expect(skip?.getAttribute("href")).toBe("#main-content");
  });

  it("renders all nine nav entries", () => {
    const el: HTMLElement = fixture.nativeElement;
    const links = el.querySelectorAll("nav.sidenav a");
    expect(links.length).toBe(9);
  });

  it("renders the Data Sentinel brand", () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector(".brand-name")?.textContent?.trim()).toBe(
      "Data Sentinel",
    );
  });
});
