import { JobId } from "../value-objects/JobId.js";
import { BackendType } from "../value-objects/BackendType.js";
import { ValidationError } from "../errors/DomainError.js";

export type JobStatus = "queued" | "active" | "completed" | "failed";

export interface JobProps {
  id: JobId;
  status: JobStatus;
  progress: number;
  backend: BackendType;
  result?: unknown;
  error?: string;
  createdAt: Date;
  updatedAt: Date;
}

export class Job {
  readonly id: JobId;
  readonly status: JobStatus;
  readonly progress: number;
  readonly backend: BackendType;
  readonly result: unknown | undefined;
  readonly error: string | undefined;
  readonly createdAt: Date;
  readonly updatedAt: Date;

  private constructor(props: JobProps) {
    this.id = props.id;
    this.status = props.status;
    this.progress = props.progress;
    this.backend = props.backend;
    this.result = props.result;
    this.error = props.error;
    this.createdAt = props.createdAt;
    this.updatedAt = props.updatedAt;
  }

  static create(backend: BackendType, id?: JobId): Job {
    const now = new Date();
    return new Job({
      id: id ?? JobId.create(),
      status: "queued",
      progress: 0,
      backend,
      createdAt: now,
      updatedAt: now,
    });
  }

  static reconstitute(props: JobProps): Job {
    return new Job(props);
  }

  updateProgress(progress: number): Job {
    if (progress < 0 || progress > 100) {
      throw new ValidationError(
        `Progress must be between 0 and 100. Received: ${progress}`
      );
    }
    if (this.status === "completed" || this.status === "failed") {
      throw new ValidationError(
        `Cannot update progress on a ${this.status} job`
      );
    }
    return new Job({
      id: this.id,
      status: progress > 0 ? "active" : this.status,
      progress,
      backend: this.backend,
      result: this.result,
      error: this.error,
      createdAt: this.createdAt,
      updatedAt: new Date(),
    });
  }

  complete(result: unknown): Job {
    if (this.status === "completed" || this.status === "failed") {
      throw new ValidationError(
        `Cannot complete a ${this.status} job`
      );
    }
    return new Job({
      id: this.id,
      status: "completed",
      progress: 100,
      backend: this.backend,
      result,
      error: undefined,
      createdAt: this.createdAt,
      updatedAt: new Date(),
    });
  }

  fail(error: string): Job {
    if (this.status === "completed") {
      throw new ValidationError("Cannot fail a completed job");
    }
    return new Job({
      id: this.id,
      status: "failed",
      progress: this.progress,
      backend: this.backend,
      result: undefined,
      error,
      createdAt: this.createdAt,
      updatedAt: new Date(),
    });
  }

  isTerminal(): boolean {
    return this.status === "completed" || this.status === "failed";
  }
}
