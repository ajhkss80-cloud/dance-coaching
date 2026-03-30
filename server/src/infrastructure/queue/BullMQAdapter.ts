import { Queue, Job as BullJob } from "bullmq";
import type Redis from "ioredis";
import { IJobQueue, JobPayload } from "../../application/ports/IJobQueue.js";
import { Job, JobStatus } from "../../domain/entities/Job.js";
import { JobId } from "../../domain/value-objects/JobId.js";
import { BackendType } from "../../domain/value-objects/BackendType.js";

function mapBullState(state: string | undefined): JobStatus {
  switch (state) {
    case "completed":
      return "completed";
    case "failed":
      return "failed";
    case "active":
      return "active";
    case "waiting":
    case "delayed":
    case "prioritized":
    default:
      return "queued";
  }
}

export class BullMQAdapter implements IJobQueue {
  private queue: Queue;

  constructor(queueName: string, connection: Redis) {
    this.queue = new Queue(queueName, {
      connection,
    });
  }

  async enqueue(payload: JobPayload): Promise<string> {
    const job = await this.queue.add(payload.type, payload.data, {
      removeOnComplete: false,
      removeOnFail: false,
    });
    return job.id!;
  }

  async getJob(id: string): Promise<Job | null> {
    const bullJob: BullJob | undefined = await this.queue.getJob(id);
    if (!bullJob) {
      return null;
    }

    const state = await bullJob.getState();
    const status = mapBullState(state);
    const progress =
      typeof bullJob.progress === "number" ? bullJob.progress : 0;
    const backend = (bullJob.data as Record<string, unknown>).backend;

    return Job.reconstitute({
      id: JobId.from(bullJob.id!),
      status,
      progress,
      backend: BackendType.from(
        typeof backend === "string" ? backend : "cloud"
      ),
      result: status === "completed" ? bullJob.returnvalue : undefined,
      error:
        status === "failed" && bullJob.failedReason
          ? bullJob.failedReason
          : undefined,
      createdAt: new Date(bullJob.timestamp),
      updatedAt: new Date(bullJob.processedOn ?? bullJob.timestamp),
    });
  }

  async getProgress(id: string): Promise<number> {
    const bullJob = await this.queue.getJob(id);
    if (!bullJob) {
      return 0;
    }
    return typeof bullJob.progress === "number" ? bullJob.progress : 0;
  }

  async close(): Promise<void> {
    await this.queue.close();
  }
}
