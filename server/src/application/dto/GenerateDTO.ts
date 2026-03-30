import { JobStatus } from "../../domain/entities/Job.js";

export interface CreateGenerateJobDTO {
  avatarPath: string;
  referencePath: string;
  backend?: string;
  maxDuration?: number;
  segmentLength?: number;
}

export interface GenerateJobStatusDTO {
  jobId: string;
  status: JobStatus;
  progress: number;
  progressMessage?: string;
  result?: GenerateResultDTO;
  error?: string;
}

export interface GenerateResultDTO {
  outputUrl: string;
  duration: number;
  segmentCount: number;
  backend: string;
}
