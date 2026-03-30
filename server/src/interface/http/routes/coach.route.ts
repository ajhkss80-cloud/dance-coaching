import type { FastifyPluginAsync } from "fastify";
import { coachParamsSchema } from "../schemas/coach.schema.js";
import { Container } from "../../../di/container.js";
import {
  ValidationError,
  NotFoundError,
} from "../../../domain/errors/DomainError.js";

export interface CoachRouteOptions {
  container: Container;
}

const coachRoutes: FastifyPluginAsync<CoachRouteOptions> = async (
  fastify,
  opts
) => {
  const { startCoaching, getCoachResult, storage } = opts.container;

  fastify.post("/api/coach", async (request, reply) => {
    const parts = request.parts();
    let userVideoPath = "";
    let referenceVideoPath = "";

    for await (const part of parts) {
      if (part.type === "file") {
        if (part.fieldname === "userVideo") {
          userVideoPath = await storage.saveFile(
            part.file,
            part.filename,
            `upload-${Date.now()}`
          );
        } else if (part.fieldname === "referenceVideo") {
          referenceVideoPath = await storage.saveFile(
            part.file,
            part.filename,
            `upload-${Date.now()}`
          );
        }
      }
    }

    try {
      const jobId = await startCoaching.execute({
        userVideoPath,
        referenceVideoPath,
      });

      return reply.status(201).send({
        jobId,
        message: "Coaching job created",
      });
    } catch (err) {
      if (err instanceof ValidationError) {
        return reply.status(400).send({ error: err.message });
      }
      throw err;
    }
  });

  fastify.get<{ Params: { jobId: string } }>(
    "/api/coach/:jobId",
    async (request, reply) => {
      const paramResult = coachParamsSchema.safeParse(request.params);
      if (!paramResult.success) {
        return reply.status(400).send({
          error: "Invalid jobId",
          details: paramResult.error.issues,
        });
      }

      try {
        const result = await getCoachResult.execute(paramResult.data.jobId);
        return reply.send(result);
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

export default coachRoutes;
