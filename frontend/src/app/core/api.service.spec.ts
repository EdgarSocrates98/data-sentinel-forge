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

  it("listSnapshots() GETs /snapshots with platform + job_id params", () => {
    service
      .listSnapshots({ platform: "glue", jobId: "job a b" })
      .subscribe((rows) => {
        expect(rows.length).toBe(1);
        expect(rows[0]?.snapshot_id).toBe("snap-1");
      });
    const req = http.expectOne(
      (r) =>
        r.url === `${environment.apiBaseUrl}/snapshots` &&
        r.params.get("platform") === "glue" &&
        r.params.get("job_id") === "job a b",
    );
    expect(req.request.method).toBe("GET");
    req.flush([
      {
        snapshot_id: "snap-1",
        platform: "glue",
        job_id: "job a b",
        run_id: "run-1",
        runtime: null,
        started_at: "2026-05-19T12:00:00Z",
        ended_at: null,
        duration_s: 10,
        input_bytes: null,
        output_bytes: null,
        resource_metrics: {},
        failure: null,
        config_fingerprint: null,
        dataset_refs: [],
        cost_observations: {},
        provenance: "test",
        limitations: [],
      },
    ]);
  });

  it("compareSnapshots() POSTs /history/compare", () => {
    service
      .compareSnapshots({ snapshot_id: "s1", baseline: "median" })
      .subscribe((res) => {
        expect(res.comparable).toBe(false);
      });
    const req = http.expectOne(`${environment.apiBaseUrl}/history/compare`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({
      snapshot_id: "s1",
      baseline: "median",
    });
    req.flush({
      comparable: false,
      incomparability_reasons: ["nenhum baseline elegível"],
      duration_delta_s: null,
      duration_delta_pct: null,
      resource_deltas: {},
      volume_delta_input: null,
      volume_delta_output: null,
      failure_regression: null,
      config_drift: [],
      quality_changes: [],
      cost_delta: {},
      limitations: ["comparação não fabricada"],
      baseline_snapshot_ids: [],
      regression_findings: [],
    });
  });

  it("listRegressions() GETs /history/regressions with encoded params", () => {
    service
      .listRegressions("job a", "snap 9")
      .subscribe((rows) => expect(rows.length).toBe(0));
    const req = http.expectOne(
      (r) =>
        r.url === `${environment.apiBaseUrl}/history/regressions` &&
        r.params.get("job_id") === "job a" &&
        r.params.get("current_id") === "snap 9",
    );
    expect(req.request.method).toBe("GET");
    req.flush([]);
  });

  it("watch endpoints hit the documented routes", () => {
    service.createWatch({
      watch_id: "w1",
      workload: "job",
      platform: "glue",
      source: "local",
      metrics: ["duration_s"],
      rule: "regression",
      interval_s: 60,
      severity: "HIGH",
    }).subscribe();
    service.runWatch("w1").subscribe();
    service.pauseWatch("w1").subscribe();
    service.resumeWatch("w1").subscribe();
    service.deleteWatch("w1").subscribe();
    service.listWatches().subscribe();
    service.listAlerts().subscribe();

    const base = environment.apiBaseUrl;
    const create = http.expectOne({
      url: `${base}/watches`,
      method: "POST",
    });
    create.flush({ watch_id: "w1", enabled: false });
    expect(
      http.expectOne(`${base}/watches/w1/run`).request.method,
    ).toBe("POST");
    expect(
      http.expectOne(`${base}/watches/w1/pause`).request.method,
    ).toBe("POST");
    expect(
      http.expectOne(`${base}/watches/w1/resume`).request.method,
    ).toBe("POST");
    expect(
      http.expectOne(`${base}/watches/w1/delete`).request.method,
    ).toBe("POST");
    http
      .expectOne({ url: `${base}/watches`, method: "GET" })
      .flush([]);
    http.expectOne(`${base}/alerts`).flush([]);
  });

  it("remediation endpoints hit the documented routes", () => {
    service.listPlans().subscribe();
    service.getPlan("rp-1").subscribe();
    service.submitPlan("rp-1").subscribe();
    service.approvePlan("rp-1", "edgar").subscribe();
    service.rejectPlan("rp-1", "not safe").subscribe();
    service.dryRunPlan("rp-1").subscribe();
    service.executeLocalPlan("rp-1").subscribe();
    service
      .createPlan({
        finding: {
          explanation: "x",
          category: "reliability",
          severity: "HIGH",
          status: "confirmed",
          recommendations: ["do y"],
        },
      })
      .subscribe();

    const base = environment.apiBaseUrl;
    http
      .expectOne({ url: `${base}/remediation/plans`, method: "GET" })
      .flush([]);
    http.expectOne(`${base}/remediation/plans/rp-1`).flush({});
    expect(
      http.expectOne(`${base}/remediation/plans/rp-1/submit`).request.method,
    ).toBe("POST");
    const approve = http.expectOne(
      `${base}/remediation/plans/rp-1/approve`,
    );
    expect(approve.request.method).toBe("POST");
    expect(approve.request.body).toEqual({ approver: "edgar" });
    approve.flush({});
    const reject = http.expectOne(
      `${base}/remediation/plans/rp-1/reject`,
    );
    expect(reject.request.body).toEqual({ reason: "not safe" });
    reject.flush({});
    expect(
      http.expectOne(`${base}/remediation/plans/rp-1/dry-run`).request
        .method,
    ).toBe("POST");
    expect(
      http.expectOne(`${base}/remediation/plans/rp-1/execute-local`)
        .request.method,
    ).toBe("POST");
    const create = http.expectOne({
      url: `${base}/remediation/plans`,
      method: "POST",
    });
    expect(create.request.body.finding.explanation).toBe("x");
    create.flush({});
  });
});
