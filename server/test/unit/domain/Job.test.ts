import { describe, it, expect } from "vitest";
import { Job } from "../../../src/domain/entities/Job.js";
import { BackendType } from "../../../src/domain/value-objects/BackendType.js";
import { JobId } from "../../../src/domain/value-objects/JobId.js";
import { ValidationError } from "../../../src/domain/errors/DomainError.js";

describe("Job Entity", () => {
  const backend = BackendType.cloud();

  it("should create a new job with queued status", () => {
    const job = Job.create(backend);

    expect(job.status).toBe("queued");
    expect(job.progress).toBe(0);
    expect(job.backend.isCloud()).toBe(true);
    expect(job.result).toBeUndefined();
    expect(job.error).toBeUndefined();
    expect(job.createdAt).toBeInstanceOf(Date);
    expect(job.updatedAt).toBeInstanceOf(Date);
  });

  it("should create a job with a specific id", () => {
    const id = JobId.from("test-id-123");
    const job = Job.create(backend, id);

    expect(job.id.toString()).toBe("test-id-123");
  });

  describe("updateProgress", () => {
    it("should update progress and transition to active", () => {
      const job = Job.create(backend);
      const updated = job.updateProgress(50);

      expect(updated.progress).toBe(50);
      expect(updated.status).toBe("active");
      expect(updated.updatedAt.getTime()).toBeGreaterThanOrEqual(
        job.updatedAt.getTime()
      );
    });

    it("should keep queued status at 0 progress", () => {
      const job = Job.create(backend);
      const updated = job.updateProgress(0);

      expect(updated.status).toBe("queued");
      expect(updated.progress).toBe(0);
    });

    it("should reject negative progress", () => {
      const job = Job.create(backend);
      expect(() => job.updateProgress(-1)).toThrow(ValidationError);
    });

    it("should reject progress over 100", () => {
      const job = Job.create(backend);
      expect(() => job.updateProgress(101)).toThrow(ValidationError);
    });

    it("should reject progress update on completed job", () => {
      const job = Job.create(backend).complete({ url: "/output.mp4" });
      expect(() => job.updateProgress(50)).toThrow(ValidationError);
    });

    it("should reject progress update on failed job", () => {
      const job = Job.create(backend).fail("some error");
      expect(() => job.updateProgress(50)).toThrow(ValidationError);
    });
  });

  describe("complete", () => {
    it("should mark job as completed with result", () => {
      const job = Job.create(backend).updateProgress(90);
      const result = { url: "/output.mp4", duration: 30 };
      const completed = job.complete(result);

      expect(completed.status).toBe("completed");
      expect(completed.progress).toBe(100);
      expect(completed.result).toEqual(result);
      expect(completed.error).toBeUndefined();
    });

    it("should complete a queued job directly", () => {
      const job = Job.create(backend);
      const completed = job.complete({ fast: true });

      expect(completed.status).toBe("completed");
      expect(completed.progress).toBe(100);
    });

    it("should reject completing an already completed job", () => {
      const job = Job.create(backend).complete({ done: true });
      expect(() => job.complete({ again: true })).toThrow(ValidationError);
    });

    it("should reject completing a failed job", () => {
      const job = Job.create(backend).fail("error");
      expect(() => job.complete({ result: true })).toThrow(ValidationError);
    });
  });

  describe("fail", () => {
    it("should mark job as failed with error message", () => {
      const job = Job.create(backend).updateProgress(30);
      const failed = job.fail("Pipeline crashed");

      expect(failed.status).toBe("failed");
      expect(failed.error).toBe("Pipeline crashed");
      expect(failed.result).toBeUndefined();
      expect(failed.progress).toBe(30);
    });

    it("should fail a queued job", () => {
      const job = Job.create(backend);
      const failed = job.fail("Queue timeout");

      expect(failed.status).toBe("failed");
      expect(failed.error).toBe("Queue timeout");
    });

    it("should reject failing a completed job", () => {
      const job = Job.create(backend).complete({ done: true });
      expect(() => job.fail("too late")).toThrow(ValidationError);
    });
  });

  describe("isTerminal", () => {
    it("should return false for queued job", () => {
      expect(Job.create(backend).isTerminal()).toBe(false);
    });

    it("should return false for active job", () => {
      expect(Job.create(backend).updateProgress(50).isTerminal()).toBe(false);
    });

    it("should return true for completed job", () => {
      expect(Job.create(backend).complete({}).isTerminal()).toBe(true);
    });

    it("should return true for failed job", () => {
      expect(Job.create(backend).fail("err").isTerminal()).toBe(true);
    });
  });

  describe("immutability", () => {
    it("should not mutate original job on updateProgress", () => {
      const original = Job.create(backend);
      const updated = original.updateProgress(50);

      expect(original.progress).toBe(0);
      expect(original.status).toBe("queued");
      expect(updated.progress).toBe(50);
      expect(updated.status).toBe("active");
    });
  });
});
