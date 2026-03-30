import { ValidationError } from "../errors/DomainError.js";

const VALID_BACKENDS = ["cloud", "local"] as const;
type BackendTypeValue = (typeof VALID_BACKENDS)[number];

export class BackendType {
  private constructor(private readonly value: BackendTypeValue) {}

  static from(raw: string): BackendType {
    if (!VALID_BACKENDS.includes(raw as BackendTypeValue)) {
      throw new ValidationError(
        `BackendType must be one of: ${VALID_BACKENDS.join(", ")}. Received: "${raw}"`
      );
    }
    return new BackendType(raw as BackendTypeValue);
  }

  static cloud(): BackendType {
    return new BackendType("cloud");
  }

  static local(): BackendType {
    return new BackendType("local");
  }

  isCloud(): boolean {
    return this.value === "cloud";
  }

  isLocal(): boolean {
    return this.value === "local";
  }

  toString(): string {
    return this.value;
  }

  equals(other: BackendType): boolean {
    return this.value === other.value;
  }
}
