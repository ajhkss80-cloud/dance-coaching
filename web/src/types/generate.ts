import type { JobStatus } from "./api";

export interface GenerateFormData {
  avatarImage: File;
  referenceVideo: File;
  backend: string;
  maxDuration: number;
  segmentLength: number;
}

export interface GenerateResult {
  outputUrl: string;
  duration: number;
  segmentCount: number;
  backend: string;
}

export interface GenerateJobStatus {
  jobId: string;
  status: JobStatus;
  progress: number;
  progressMessage?: string;
  result?: GenerateResult;
  error?: string;
}
