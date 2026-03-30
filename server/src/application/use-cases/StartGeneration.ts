import { GenerateRequest } from "../../domain/entities/GenerateRequest.js";
import { BackendType } from "../../domain/value-objects/BackendType.js";
import { ValidationError } from "../../domain/errors/DomainError.js";
import { IJobQueue } from "../ports/IJobQueue.js";
import { IStorage } from "../ports/IStorage.js";
import { CreateGenerateJobDTO } from "../dto/GenerateDTO.js";

const DEFAULT_MAX_DURATION = 60;
const DEFAULT_SEGMENT_LENGTH = 10;
const DEFAULT_BACKEND = "cloud";

export class StartGeneration {
  constructor(
    private readonly jobQueue: IJobQueue,
    private readonly storage: IStorage
  ) {}

  async execute(dto: CreateGenerateJobDTO): Promise<string> {
    if (!dto.avatarPath || dto.avatarPath.trim().length === 0) {
      throw new ValidationError("avatarPath is required");
    }

    if (!dto.referencePath || dto.referencePath.trim().length === 0) {
      throw new ValidationError("referencePath is required");
    }

    const backend = BackendType.from(dto.backend ?? DEFAULT_BACKEND);

    const request = GenerateRequest.create({
      avatarPath: dto.avatarPath,
      referencePath: dto.referencePath,
      backend,
      options: {
        maxDuration: dto.maxDuration ?? DEFAULT_MAX_DURATION,
        segmentLength: dto.segmentLength ?? DEFAULT_SEGMENT_LENGTH,
      },
    });

    const avatarExists = await this.storage.fileExists(request.avatarPath);
    if (!avatarExists) {
      throw new ValidationError(
        `Avatar file not found: ${request.avatarPath}`
      );
    }

    const referenceExists = await this.storage.fileExists(
      request.referencePath
    );
    if (!referenceExists) {
      throw new ValidationError(
        `Reference file not found: ${request.referencePath}`
      );
    }

    const jobId = await this.jobQueue.enqueue({
      type: "generate",
      data: {
        avatarPath: request.avatarPath,
        referencePath: request.referencePath,
        backend: request.backend.toString(),
        maxDuration: request.options.maxDuration,
        segmentLength: request.options.segmentLength,
      },
    });

    return jobId;
  }
}
