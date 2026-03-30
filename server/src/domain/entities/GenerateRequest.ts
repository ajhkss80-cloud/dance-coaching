import { BackendType } from "../value-objects/BackendType.js";
import { ValidationError } from "../errors/DomainError.js";

export interface GenerateRequestOptions {
  maxDuration: number;
  segmentLength: number;
}

export interface GenerateRequestProps {
  avatarPath: string;
  referencePath: string;
  backend: BackendType;
  options: GenerateRequestOptions;
}

export class GenerateRequest {
  readonly avatarPath: string;
  readonly referencePath: string;
  readonly backend: BackendType;
  readonly options: GenerateRequestOptions;

  private constructor(props: GenerateRequestProps) {
    this.avatarPath = props.avatarPath;
    this.referencePath = props.referencePath;
    this.backend = props.backend;
    this.options = Object.freeze({ ...props.options });
  }

  static create(props: GenerateRequestProps): GenerateRequest {
    GenerateRequest.validate(props);
    return new GenerateRequest(props);
  }

  private static validate(props: GenerateRequestProps): void {
    const errors: string[] = [];

    if (!props.avatarPath || props.avatarPath.trim().length === 0) {
      errors.push("avatarPath must be a non-empty string");
    }

    if (!props.referencePath || props.referencePath.trim().length === 0) {
      errors.push("referencePath must be a non-empty string");
    }

    if (
      typeof props.options.maxDuration !== "number" ||
      props.options.maxDuration < 1 ||
      props.options.maxDuration > 300
    ) {
      errors.push("maxDuration must be between 1 and 300 seconds");
    }

    if (
      typeof props.options.segmentLength !== "number" ||
      props.options.segmentLength < 3 ||
      props.options.segmentLength > 30
    ) {
      errors.push("segmentLength must be between 3 and 30 seconds");
    }

    if (errors.length > 0) {
      throw new ValidationError(
        `Invalid GenerateRequest: ${errors.join("; ")}`
      );
    }
  }
}
