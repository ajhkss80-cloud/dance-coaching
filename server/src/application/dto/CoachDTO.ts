import { JobStatus } from "../../domain/entities/Job.js";

export interface CreateCoachJobDTO {
  userVideoPath: string;
  referenceVideoPath: string;
}

export interface CoachJobStatusDTO {
  jobId: string;
  status: JobStatus;
  progress: number;
  result?: CoachResultDTO;
  error?: string;
}

export interface CoachResultDTO {
  overallScore: number;
  jointScores: Record<string, number>;
  feedback: string[];
}
