import { Job } from "../../domain/entities/Job.js";

export interface JobPayload {
  type: "generate" | "coach";
  data: Record<string, unknown>;
}

export interface IJobQueue {
  enqueue(payload: JobPayload): Promise<string>;
  getJob(id: string): Promise<Job | null>;
  getProgress(id: string): Promise<number>;
}
