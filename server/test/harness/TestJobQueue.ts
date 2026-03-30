import { IJobQueue, JobPayload } from "../../src/application/ports/IJobQueue.js";
import { Job, JobStatus } from "../../src/domain/entities/Job.js";
import { JobId } from "../../src/domain/value-objects/JobId.js";
import { BackendType } from "../../src/domain/value-objects/BackendType.js";

interface StoredJob {
  id: string;
  payload: JobPayload;
  status: JobStatus;
  progress: number;
  result?: unknown;
  error?: string;
  createdAt: Date;
}

let idCounter = 0;

export class TestJobQueue implements IJobQueue {
  private jobs = new Map<string, StoredJob>();

  async enqueue(payload: JobPayload): Promise<string> {
    idCounter += 1;
    const id = `test-job-${idCounter}`;
    this.jobs.set(id, {
      id,
      payload,
      status: "queued",
      progress: 0,
      createdAt: new Date(),
    });
    return id;
  }

  async getJob(id: string): Promise<Job | null> {
    const stored = this.jobs.get(id);
    if (!stored) return null;

    const backend =
      typeof stored.payload.data.backend === "string"
        ? BackendType.from(stored.payload.data.backend)
        : BackendType.cloud();

    return Job.reconstitute({
      id: JobId.from(stored.id),
      status: stored.status,
      progress: stored.progress,
      backend,
      result: stored.result,
      error: stored.error,
      createdAt: stored.createdAt,
      updatedAt: new Date(),
    });
  }

  async getProgress(id: string): Promise<number> {
    const stored = this.jobs.get(id);
    return stored?.progress ?? 0;
  }

  // Test helpers

  simulateProgress(id: string, progress: number): void {
    const stored = this.jobs.get(id);
    if (stored) {
      stored.progress = progress;
      stored.status = progress > 0 ? "active" : stored.status;
    }
  }

  simulateCompletion(id: string, result: unknown): void {
    const stored = this.jobs.get(id);
    if (stored) {
      stored.status = "completed";
      stored.progress = 100;
      stored.result = result;
    }
  }

  simulateFailure(id: string, error: string): void {
    const stored = this.jobs.get(id);
    if (stored) {
      stored.status = "failed";
      stored.error = error;
    }
  }

  getStoredPayload(id: string): JobPayload | undefined {
    return this.jobs.get(id)?.payload;
  }

  clear(): void {
    this.jobs.clear();
    idCounter = 0;
  }
}
