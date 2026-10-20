/**
 * Jasmine compatibility layer for the Vitest unit-test runner.
 *
 * Registered via `architect.test.options.setupFiles` in angular.json
 * (`@angular/build:unit-test`, runner "vitest", globals enabled).
 *
 * The Karma -> Vitest migration keeps all *.spec.ts files unchanged. Vitest
 * globals already cover describe/it/beforeEach/expect plus the Jest-style
 * matcher set, but this suite also uses three Jasmine-only APIs:
 *
 *   - `spyOn(obj, "method")` global returning a spy with `.and.*` and
 *     `.calls.mostRecent()` accessors (used in reports.component.spec.ts)
 *   - `expect(x).toBeTrue()` / `expect(x).toBeFalse()` matchers
 *
 * This file installs minimal shims for exactly those APIs and mirrors
 * Jasmine's semantics: a spy stubs by default and is restored after each
 * test.
 */
import { afterEach, expect, vi, type MockInstance } from "vitest";

declare module "vitest" {
  interface Assertion<T> {
    /** Jasmine parity: strict `=== true` assertion. */
    toBeTrue(): void;
    /** Jasmine parity: strict `=== false` assertion. */
    toBeFalse(): void;
  }
  interface AsymmetricMatchersContaining {
    toBeTrue(): void;
    toBeFalse(): void;
  }
}

expect.extend({
  toBeTrue(received: unknown) {
    const pass = received === true;
    return {
      pass,
      message: () =>
        `expected ${JSON.stringify(received)} ${pass ? "not " : ""}to be true`,
    };
  },
  toBeFalse(received: unknown) {
    const pass = received === false;
    return {
      pass,
      message: () =>
        `expected ${JSON.stringify(received)} ${pass ? "not " : ""}to be false`,
    };
  },
});

type AnyFn = (this: unknown, ...args: unknown[]) => unknown;

/** MockInstance augmented with the Jasmine `Spy` accessors the suite uses. */
export interface JasmineCompatSpy extends MockInstance {
  and: {
    returnValue(value: unknown): JasmineCompatSpy;
    callFake(fn: AnyFn): JasmineCompatSpy;
    callThrough(): JasmineCompatSpy;
    stub(): JasmineCompatSpy;
  };
  calls: {
    mostRecent(): { args: unknown[] };
    all(): { args: unknown[] }[];
    count(): number;
    reset(): void;
  };
}

declare global {
  // eslint-disable-next-line no-var
  var spyOn: <T extends object, K extends keyof T>(
    obj: T,
    method: K,
  ) => JasmineCompatSpy;
}

const spyRestorers: Array<() => void> = [];

function jasmineSpyOn<T extends object, K extends keyof T>(
  target: T,
  method: K,
): JasmineCompatSpy {
  const record = target as Record<PropertyKey, unknown>;
  const original = record[method];
  let spy: MockInstance;

  if (typeof original === "function") {
    spy = vi.spyOn(target, method as never) as unknown as MockInstance;
    // Jasmine's spyOn replaces the method with a stub; it does NOT call
    // through to the original implementation (unlike vi.spyOn).
    spy.mockImplementation((() => undefined) as never);
    spyRestorers.push(() => spy.mockRestore());
  } else {
    // jsdom lacks a few DOM APIs that Chrome provides under Karma
    // (URL.createObjectURL / URL.revokeObjectURL). Install a stub so specs
    // written against real browsers keep running under jsdom.
    spy = vi.fn();
    Object.defineProperty(target, method, {
      configurable: true,
      writable: true,
      enumerable: false,
      value: spy,
    });
    spyRestorers.push(() => {
      delete record[method];
    });
  }

  const compat = spy as JasmineCompatSpy;
  compat.and = {
    returnValue(value: unknown): JasmineCompatSpy {
      spy.mockReturnValue(value as never);
      return compat;
    },
    callFake(fn: AnyFn): JasmineCompatSpy {
      spy.mockImplementation(fn as never);
      return compat;
    },
    callThrough(): JasmineCompatSpy {
      if (typeof original === "function") {
        spy.mockImplementation(function (this: unknown, ...args: unknown[]) {
          return (original as AnyFn).apply(this, args);
        } as never);
      }
      return compat;
    },
    stub(): JasmineCompatSpy {
      spy.mockImplementation((() => undefined) as never);
      return compat;
    },
  };
  compat.calls = {
    mostRecent() {
      return { args: [...(spy.mock.calls.at(-1) ?? [])] };
    },
    all() {
      return spy.mock.calls.map((args) => ({ args: [...args] }));
    },
    count() {
      return spy.mock.calls.length;
    },
    reset() {
      spy.mockClear();
    },
  };
  return compat;
}

(globalThis as Record<string, unknown>)["spyOn"] = jasmineSpyOn;

afterEach(() => {
  // Jasmine restores spies between specs; mirror that for every spy created
  // through this global so mocks never leak across tests.
  for (const restore of spyRestorers.splice(0)) {
    restore();
  }
});
