import { ComponentFixture, TestBed } from "@angular/core/testing";

import { InvestigationsComponent } from "./investigations.component";

describe("InvestigationsComponent", () => {
  let fixture: ComponentFixture<InvestigationsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InvestigationsComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(InvestigationsComponent);
    fixture.detectChanges();
  });

  it("renders a real page with heading, badge and planned capabilities", () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector("h1")?.textContent?.trim()).toBe("Investigações");
    expect(el.querySelector(".ds-badge--wip")?.textContent).toContain(
      "Em construção",
    );
    expect(el.querySelectorAll(".planned-list li").length).toBe(6);
  });
});
