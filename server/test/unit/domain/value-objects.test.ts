import { describe, it, expect } from "vitest";
import { JobId } from "../../../src/domain/value-objects/JobId.js";
import { BackendType } from "../../../src/domain/value-objects/BackendType.js";
import { Score } from "../../../src/domain/value-objects/Score.js";
import { ValidationError } from "../../../src/domain/errors/DomainError.js";

describe("JobId", () => {
  it("should create a unique id via create()", () => {
    const id1 = JobId.create();
    const id2 = JobId.create();

    expect(id1.toString()).toBeTruthy();
    expect(id2.toString()).toBeTruthy();
    expect(id1.toString()).not.toBe(id2.toString());
  });

  it("should reconstruct from a valid string", () => {
    const id = JobId.from("abc-123");
    expect(id.toString()).toBe("abc-123");
  });

  it("should trim whitespace", () => {
    const id = JobId.from("  abc-123  ");
    expect(id.toString()).toBe("abc-123");
  });

  it("should reject empty string", () => {
    expect(() => JobId.from("")).toThrow(ValidationError);
  });

  it("should reject whitespace-only string", () => {
    expect(() => JobId.from("   ")).toThrow(ValidationError);
  });

  it("should support equality check", () => {
    const a = JobId.from("same-id");
    const b = JobId.from("same-id");
    const c = JobId.from("different-id");

    expect(a.equals(b)).toBe(true);
    expect(a.equals(c)).toBe(false);
  });
});

describe("BackendType", () => {
  it("should create cloud backend", () => {
    const backend = BackendType.from("cloud");
    expect(backend.isCloud()).toBe(true);
    expect(backend.isLocal()).toBe(false);
    expect(backend.toString()).toBe("cloud");
  });

  it("should create local backend", () => {
    const backend = BackendType.from("local");
    expect(backend.isCloud()).toBe(false);
    expect(backend.isLocal()).toBe(true);
    expect(backend.toString()).toBe("local");
  });

  it("should create via static factory cloud()", () => {
    const backend = BackendType.cloud();
    expect(backend.isCloud()).toBe(true);
  });

  it("should create via static factory local()", () => {
    const backend = BackendType.local();
    expect(backend.isLocal()).toBe(true);
  });

  it("should reject invalid backend string", () => {
    expect(() => BackendType.from("gpu")).toThrow(ValidationError);
  });

  it("should reject empty string", () => {
    expect(() => BackendType.from("")).toThrow(ValidationError);
  });

  it("should support equality check", () => {
    const a = BackendType.cloud();
    const b = BackendType.cloud();
    const c = BackendType.local();

    expect(a.equals(b)).toBe(true);
    expect(a.equals(c)).toBe(false);
  });
});

describe("Score", () => {
  it("should create score from valid number", () => {
    const score = Score.from(85);
    expect(score.toNumber()).toBe(85);
  });

  it("should accept 0", () => {
    const score = Score.from(0);
    expect(score.toNumber()).toBe(0);
  });

  it("should accept 100", () => {
    const score = Score.from(100);
    expect(score.toNumber()).toBe(100);
  });

  it("should round to two decimal places", () => {
    const score = Score.from(85.456);
    expect(score.toNumber()).toBe(85.46);
  });

  it("should format as percentage", () => {
    expect(Score.from(85).toPercentage()).toBe("85%");
    expect(Score.from(0).toPercentage()).toBe("0%");
    expect(Score.from(100).toPercentage()).toBe("100%");
    expect(Score.from(33.33).toPercentage()).toBe("33%");
  });

  it("should reject negative numbers", () => {
    expect(() => Score.from(-1)).toThrow(ValidationError);
  });

  it("should reject numbers over 100", () => {
    expect(() => Score.from(101)).toThrow(ValidationError);
  });

  it("should reject NaN", () => {
    expect(() => Score.from(NaN)).toThrow(ValidationError);
  });

  it("should support equality check", () => {
    const a = Score.from(85);
    const b = Score.from(85);
    const c = Score.from(90);

    expect(a.equals(b)).toBe(true);
    expect(a.equals(c)).toBe(false);
  });
});
