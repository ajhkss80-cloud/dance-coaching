import type { JobStatus } from "./api";

export interface CoachFormData {
  userVideo: File;
  referenceVideo: File;
}

export interface CoachResult {
  overallScore: number;
  jointScores: Record<string, number>;
  feedback: string[];
}

export interface CoachJobStatus {
  jobId: string;
  status: JobStatus;
  progress: number;
  result?: CoachResult;
  error?: string;
}
