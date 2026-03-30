import { NotFoundError, ValidationError } from "../../domain/errors/DomainError.js";
import { IJobQueue } from "../ports/IJobQueue.js";
import { CoachJobStatusDTO, CoachResultDTO } from "../dto/CoachDTO.js";

export class GetCoachResult {
  constructor(private readonly jobQueue: IJobQueue) {}

  async execute(jobId: string): Promise<CoachJobStatusDTO> {
    if (!jobId || jobId.trim().length === 0) {
      throw new ValidationError("jobId is required");
    }

    const job = await this.jobQueue.getJob(jobId);
    if (!job) {
      throw new NotFoundError(`Job not found: ${jobId}`);
    }

    const dto: CoachJobStatusDTO = {
      jobId: job.id.toString(),
      status: job.status,
      progress: job.progress,
    };

    if (job.status === "completed" && job.result) {
      dto.result = job.result as CoachResultDTO;
    }

    if (job.status === "failed" && job.error) {
      dto.error = job.error;
    }

    return dto;
  }
}
