import type { FastifyPluginAsync } from "fastify";
import { generateParamsSchema, generateBodySchema } from "../schemas/generate.schema.js";
import { Container } from "../../../di/container.js";
import {
  DomainError,
  ValidationError,
  NotFoundError,
} from "../../../domain/errors/DomainError.js";

export interface GenerateRouteOptions {
  container: Container;
}

const generateRoutes: FastifyPluginAsync<GenerateRouteOptions> = async (
  fastify,
  opts
) => {
  const { startGeneration, getJobStatus, storage } = opts.container;

  fastify.post("/api/generate", async (request, reply) => {
    const parts = request.parts();
    let avatarPath = "";
    let referencePath = "";
    let backend: string | undefined;
    let maxDuration: number | undefined;
    let segmentLength: number | undefined;

    for await (const part of parts) {
      if (part.type === "file") {
        if (part.fieldname === "avatarImage") {
          avatarPath = await storage.saveFile(
            part.file,
            part.filename,
            `upload-${Date.now()}`
          );
        } else if (part.fieldname === "referenceVideo") {
          referencePath = await storage.saveFile(
            part.file,
            part.filename,
            `upload-${Date.now()}`
          );
        }
      } else if (part.type === "field") {
        const value = part.value as string;
        if (part.fieldname === "backend") {
          backend = value;
        } else if (part.fieldname === "maxDuration") {
          maxDuration = Number(value);
        } else if (part.fieldname === "segmentLength") {
          segmentLength = Number(value);
        }
      }
    }

    const bodyResult = generateBodySchema.safeParse({
      backend,
      maxDuration,
      segmentLength,
    });

    if (!bodyResult.success) {
      return reply.status(400).send({
        error: "Validation failed",
        details: bodyResult.error.issues,
      });
    }

    try {
      const jobId = await startGeneration.execute({
        avatarPath,
        referencePath,
        backend: bodyResult.data.backend,
        maxDuration: bodyResult.data.maxDuration,
        segmentLength: bodyResult.data.segmentLength,
      });

      return reply.status(201).send({
        jobId,
        message: "Generation job created",
      });
    } catch (err) {
      if (err instanceof ValidationError) {
        return reply.status(400).send({ error: err.message });
      }
      throw err;
    }
  });

  fastify.get<{ Params: { jobId: string } }>(
    "/api/generate/:jobId",
    async (request, reply) => {
      const paramResult = generateParamsSchema.safeParse(request.params);
      if (!paramResult.success) {
        return reply.status(400).send({
          error: "Invalid jobId",
          details: paramResult.error.issues,
        });
      }

      try {
        const status = await getJobStatus.execute(paramResult.data.jobId);
        return reply.send(status);
      } catch (err) {
        if (err instanceof NotFoundError) {
          return reply.status(404).send({ error: err.message });
        }
        if (err instanceof ValidationError) {
          return reply.status(400).send({ error: err.message });
        }
        throw err;
      }
    }
  );
};

export default generateRoutes;
