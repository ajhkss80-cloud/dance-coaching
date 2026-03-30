import { nanoid } from "nanoid";
import { ValidationError } from "../errors/DomainError.js";

export class JobId {
  private constructor(private readonly value: string) {}

  static create(): JobId {
    return new JobId(nanoid());
  }

  static from(raw: string): JobId {
    if (!raw || typeof raw !== "string" || raw.trim().length === 0) {
      throw new ValidationError("JobId must be a non-empty string");
    }
    return new JobId(raw.trim());
  }

  toString(): string {
    return this.value;
  }

  equals(other: JobId): boolean {
    return this.value === other.value;
  }
}
