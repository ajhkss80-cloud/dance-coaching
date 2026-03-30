import type { FastifyPluginAsync } from "fastify";
import { Container } from "../../../di/container.js";

export interface ConfigRouteOptions {
  container: Container;
}

const configRoutes: FastifyPluginAsync<ConfigRouteOptions> = async (
  fastify,
  opts
) => {
  const { config } = opts.container;

  fastify.get("/api/config", async (_request, reply) => {
    return reply.send({
      generationBackend: config.GENERATION_BACKEND,
      maxVideoDurationSec: config.MAX_VIDEO_DURATION_SEC,
      segmentMaxLengthSec: config.SEGMENT_MAX_LENGTH_SEC,
    });
  });
};

export default configRoutes;
