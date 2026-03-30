import { Score } from "../value-objects/Score.js";
import { ValidationError } from "../errors/DomainError.js";

export interface CoachResultProps {
  overallScore: Score;
  jointScores: Record<string, Score>;
  feedback: string[];
}

export class CoachResult {
  readonly overallScore: Score;
  readonly jointScores: Readonly<Record<string, Score>>;
  readonly feedback: readonly string[];

  private constructor(props: CoachResultProps) {
    this.overallScore = props.overallScore;
    this.jointScores = Object.freeze({ ...props.jointScores });
    this.feedback = Object.freeze([...props.feedback]);
  }

  static create(props: CoachResultProps): CoachResult {
    CoachResult.validate(props);
    return new CoachResult(props);
  }

  private static validate(props: CoachResultProps): void {
    if (!props.overallScore) {
      throw new ValidationError("overallScore is required");
    }

    if (!props.jointScores || typeof props.jointScores !== "object") {
      throw new ValidationError("jointScores must be an object");
    }

    if (!Array.isArray(props.feedback)) {
      throw new ValidationError("feedback must be an array of strings");
    }

    for (const item of props.feedback) {
      if (typeof item !== "string") {
        throw new ValidationError("Each feedback item must be a string");
      }
    }
  }

  toPlain(): {
    overallScore: number;
    jointScores: Record<string, number>;
    feedback: string[];
  } {
    const jointScores: Record<string, number> = {};
    for (const [key, score] of Object.entries(this.jointScores)) {
      jointScores[key] = score.toNumber();
    }
    return {
      overallScore: this.overallScore.toNumber(),
      jointScores,
      feedback: [...this.feedback],
    };
  }
}
