import { Job, JobStatus } from "../../domain/entities/Job.js";

export interface JobUpdateData {
  progress?: number;
  result?: unknown;
  error?: string;
}

export interface IJobRepository {
  save(job: Job): Promise<void>;
  findById(id: string): Promise<Job | null>;
  updateStatus(id: string, status: JobStatus, data?: JobUpdateData): Promise<void>;
}
