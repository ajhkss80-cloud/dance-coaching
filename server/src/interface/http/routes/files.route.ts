import type { FastifyPluginAsync } from "fastify";
import { resolve, join, normalize } from "node:path";
import { createReadStream, existsSync } from "node:fs";
import { stat } from "node:fs/promises";
import { Container } from "../../../di/container.js";
import { LocalStorageAdapter } from "../../../infrastructure/storage/LocalStorageAdapter.js";

export interface FilesRouteOptions {
  container: Container;
}

const filesRoutes: FastifyPluginAsync<FilesRouteOptions> = async (
  fastify,
  opts
) => {
  const storage = opts.container.storage;

  let outputsDir: string;
  if (storage instanceof LocalStorageAdapter) {
    outputsDir = storage.getOutputsDir();
  } else {
    outputsDir = resolve(opts.container.config.STORAGE_DIR, "outputs");
  }

  fastify.get<{ Params: { filename: string } }>(
    "/api/files/:filename",
    async (request, reply) => {
      const { filename } = request.params;

      if (!filename || filename.includes("..") || filename.includes("/") || filename.includes("\\")) {
        return reply.status(400).send({ error: "Invalid filename" });
      }

      const filePath = normalize(join(outputsDir, filename));
      const resolvedOutputs = normalize(outputsDir);

      if (!filePath.startsWith(resolvedOutputs)) {
        return reply.status(403).send({ error: "Access denied" });
      }

      try {
        const info = await stat(filePath);
        if (!info.isFile()) {
          return reply.status(404).send({ error: "File not found" });
        }
      } catch {
        return reply.status(404).send({ error: "File not found" });
      }

      const stream = createReadStream(filePath);
      return reply.type("application/octet-stream").send(stream);
    }
  );
};

export default filesRoutes;
