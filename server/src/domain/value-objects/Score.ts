import { ValidationError } from "../errors/DomainError.js";

export class Score {
  private constructor(private readonly value: number) {}

  static from(raw: number): Score {
    if (typeof raw !== "number" || Number.isNaN(raw)) {
      throw new ValidationError("Score must be a valid number");
    }
    if (raw < 0 || raw > 100) {
      throw new ValidationError(
        `Score must be between 0 and 100. Received: ${raw}`
      );
    }
    return new Score(Math.round(raw * 100) / 100);
  }

  toNumber(): number {
    return this.value;
  }

  toPercentage(): string {
    return `${Math.round(this.value)}%`;
  }

  equals(other: Score): boolean {
    return this.value === other.value;
  }
}
