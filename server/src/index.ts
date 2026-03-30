import "dotenv/config";
import Fastify from "fastify";
import cors from "@fastify/cors";
import multipart from "@fastify/multipart";
import websocket from "@fastify/websocket";
import { createContainer } from "./di/container.js";
import generateRoutes from "./interface/http/routes/generate.route.js";
import coachRoutes from "./interface/http/routes/coach.route.js";
import configRoutes from "./interface/http/routes/config.route.js";
import filesRoutes from "./interface/http/routes/files.route.js";
import jobProgressWs from "./interface/ws/job-progress.js";
import { LocalStorageAdapter } from "./infrastructure/storage/LocalStorageAdapter.js";

async function main() {
  const container = createContainer();

  const fastify = Fastify({
    logger: true,
  });

  // Register plugins
  await fastify.register(cors, { origin: true });
  await fastify.register(multipart, {
    limits: {
      fileSize: 500 * 1024 * 1024, // 500MB
    },
  });
  await fastify.register(websocket);

  // Initialize storage directories
  const storage = container.storage;
  if (storage instanceof LocalStorageAdapter) {
    await storage.init();
  }

  // Connect Redis
  if (container.redis) {
    await container.redis.connect();
  }

  // Register routes
  await fastify.register(generateRoutes, { container });
  await fastify.register(coachRoutes, { container });
  await fastify.register(configRoutes, { container });
  await fastify.register(filesRoutes, { container });
  await fastify.register(jobProgressWs, { container });

  // Health check
  fastify.get("/api/health", async () => {
    return { status: "ok", timestamp: new Date().toISOString() };
  });

  // Graceful shutdown
  const shutdown = async (signal: string) => {
    fastify.log.info(`Received ${signal}, shutting down gracefully`);
    await fastify.close();
    await container.shutdown();
    process.exit(0);
  };

  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));

  // Start server
  const port = container.config.SERVER_PORT;
  await fastify.listen({ port, host: "0.0.0.0" });
  fastify.log.info(`Server listening on port ${port}`);
}

main().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
