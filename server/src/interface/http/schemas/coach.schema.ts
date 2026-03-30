import { z } from "zod";

export const coachParamsSchema = z.object({
  jobId: z.string().min(1),
});

export type CoachParams = z.infer<typeof coachParamsSchema>;

export const coachResponseSchema = z.object({
  jobId: z.string(),
  status: z.enum(["queued", "active", "completed", "failed"]),
  progress: z.number(),
  result: z
    .object({
      overallScore: z.number(),
      jointScores: z.record(z.string(), z.number()),
      feedback: z.array(z.string()),
    })
    .optional(),
  error: z.string().optional(),
});

export const createCoachResponseSchema = z.object({
  jobId: z.string(),
  message: z.string(),
});
