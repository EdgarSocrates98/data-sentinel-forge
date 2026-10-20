import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { environment } from "../../environments/environment";
import { ApiService } from "./api.service";

describe("ApiService", () => {
  let service: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it("constructs", () => {
    expect(service).toBeTruthy();
  });

  it("health() GETs /health on the configured base URL", () => {
    service.health().subscribe((res) => {
      expect(res.status).toBe("ok");
      expect(res.version).toBe("0.1.0");
    });
    const req = http.expectOne(`${environment.apiBaseUrl}/health`);
    expect(req.request.method).toBe("GET");
    req.flush({ status: "ok", version: "0.1.0", api: "v1" });
  });

  it("capabilities() GETs /capabilities as a typed list", () => {
    service.capabilities().subscribe((caps) => {
      expect(caps.length).toBe(1);
      expect(caps[0]?.capability_id).toBe("sentinel.spark-explain");
    });
    const req = http.expectOne(`${environment.apiBaseUrl}/capabilities`);
    expect(req.request.method).toBe("GET");
    req.flush([
      {
        capability_id: "sentinel.spark-explain",
        provider: "data-sentinel",
        version: "1.0.0",
        input_types: ["diagnostic-request"],
        output_types: ["findings"],
        permissions: [],
        limitations: [],
      },
    ]);
  });

  it("createInvestigation() POSTs problem + files", () => {
    service
      .createInvestigation({ problem: "job lento", files: {} })
      .subscribe((res) => {
        expect(res.investigation_id).toBe("inv-abc");
        expect(res.status).toBe("running");
      });
    const req = http.expectOne(`${environment.apiBaseUrl}/investigations`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({ problem: "job lento", files: {} });
    req.flush({ investigation_id: "inv-abc", status: "running" });
  });
});
