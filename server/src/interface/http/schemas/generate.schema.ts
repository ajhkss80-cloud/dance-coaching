import { z } from "zod";

export const generateBodySchema = z.object({
  backend: z.enum(["cloud", "local"]).optional(),
  maxDuration: z.coerce.number().int().min(1).max(300).optional(),
  segmentLength: z.coerce.number().int().min(3).max(30).optional(),
});

export type GenerateBody = z.infer<typeof generateBodySchema>;

export const generateParamsSchema = z.object({
  jobId: z.string().min(1),
});

export type GenerateParams = z.infer<typeof generateParamsSchema>;

export const generateResponseSchema = z.object({
  jobId: z.string(),
  status: z.enum(["queued", "active", "completed", "failed"]),
  progress: z.number(),
  progressMessage: z.string().optional(),
  result: z
    .object({
      outputUrl: z.string(),
      duration: z.number(),
      segmentCount: z.number(),
      backend: z.string(),
    })
    .optional(),
  error: z.string().optional(),
});

export const createGenerateResponseSchema = z.object({
  jobId: z.string(),
  message: z.string(),
});
