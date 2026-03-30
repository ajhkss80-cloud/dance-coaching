import { ValidationError } from "../../domain/errors/DomainError.js";
import { IJobQueue } from "../ports/IJobQueue.js";
import { CreateCoachJobDTO } from "../dto/CoachDTO.js";

export class StartCoaching {
  constructor(private readonly jobQueue: IJobQueue) {}

  async execute(dto: CreateCoachJobDTO): Promise<string> {
    if (!dto.userVideoPath || dto.userVideoPath.trim().length === 0) {
      throw new ValidationError("userVideoPath is required");
    }

    if (!dto.referenceVideoPath || dto.referenceVideoPath.trim().length === 0) {
      throw new ValidationError("referenceVideoPath is required");
    }

    const jobId = await this.jobQueue.enqueue({
      type: "coach",
      data: {
        userVideoPath: dto.userVideoPath,
        referenceVideoPath: dto.referenceVideoPath,
      },
    });

    return jobId;
  }
}
