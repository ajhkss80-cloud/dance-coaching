import { z } from "zod";

const envSchema = z
  .object({
    SERVER_PORT: z.coerce.number().int().positive().default(3000),
    REDIS_URL: z.string().default("redis://localhost:6379"),
    STORAGE_DIR: z.string().default("./storage"),
    GENERATION_BACKEND: z.enum(["cloud", "local"]).default("cloud"),
    KLING_API_KEY: z.string().optional(),
    KLING_API_BASE_URL: z
      .string()
      .default("https://api.klingai.com"),
    MAX_VIDEO_DURATION_SEC: z.coerce.number().int().positive().default(180),
    SEGMENT_MAX_LENGTH_SEC: z.coerce.number().int().positive().default(10),
  })
  .superRefine((data, ctx) => {
    if (data.GENERATION_BACKEND === "cloud" && !data.KLING_API_KEY) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "KLING_API_KEY is required when GENERATION_BACKEND is 'cloud'",
        path: ["KLING_API_KEY"],
      });
    }
  });

export type EnvConfig = z.infer<typeof envSchema>;

let _config: EnvConfig | null = null;

export function loadConfig(overrides?: Partial<Record<string, string>>): EnvConfig {
  const source = { ...process.env, ...overrides };
  const result = envSchema.safeParse(source);

  if (!result.success) {
    const formatted = result.error.issues
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(`Environment validation failed:\n${formatted}`);
  }

  _config = result.data;
  return _config;
}

export function getConfig(): EnvConfig {
  if (!_config) {
    throw new Error("Config not loaded. Call loadConfig() first.");
  }
  return _config;
}
