import { NotFoundError, ValidationError } from "../../domain/errors/DomainError.js";
import { IJobQueue } from "../ports/IJobQueue.js";
import { GenerateJobStatusDTO, GenerateResultDTO } from "../dto/GenerateDTO.js";

const PROGRESS_MESSAGES: Record<string, string> = {
  queued: "Job is waiting in queue",
  active: "Processing your request",
  completed: "Generation complete",
  failed: "Generation failed",
};

function progressMessage(status: string, progress: number): string {
  if (status === "active") {
    if (progress < 25) return "Initializing pipeline";
    if (progress < 50) return "Analyzing reference video";
    if (progress < 75) return "Generating dance sequence";
    return "Finalizing output";
  }
  return PROGRESS_MESSAGES[status] ?? "Unknown status";
}

export class GetJobStatus {
  constructor(private readonly jobQueue: IJobQueue) {}

  async execute(jobId: string): Promise<GenerateJobStatusDTO> {
    if (!jobId || jobId.trim().length === 0) {
      throw new ValidationError("jobId is required");
    }

    const job = await this.jobQueue.getJob(jobId);
    if (!job) {
      throw new NotFoundError(`Job not found: ${jobId}`);
    }

    const dto: GenerateJobStatusDTO = {
      jobId: job.id.toString(),
      status: job.status,
      progress: job.progress,
      progressMessage: progressMessage(job.status, job.progress),
    };

    if (job.status === "completed" && job.result) {
      dto.result = job.result as GenerateResultDTO;
    }

    if (job.status === "failed" && job.error) {
      dto.error = job.error;
    }

    return dto;
  }
}
