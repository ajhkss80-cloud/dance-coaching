import type { FastifyPluginAsync } from "fastify";
import { Container } from "../../di/container.js";

export interface JobProgressWsOptions {
  container: Container;
}

interface ProgressMessage {
  type: "progress" | "completed" | "failed";
  jobId: string;
  progress?: number;
  result?: unknown;
  error?: string;
}

const jobProgressWs: FastifyPluginAsync<JobProgressWsOptions> = async (
  fastify,
  opts
) => {
  const { jobQueue } = opts.container;

  fastify.get<{ Params: { jobId: string } }>(
    "/api/ws/jobs/:jobId",
    { websocket: true },
    async (socket, request) => {
      const { jobId } = request.params;
      let closed = false;

      const sendMessage = (msg: ProgressMessage) => {
        if (!closed) {
          try {
            socket.send(JSON.stringify(msg));
          } catch {
            closed = true;
          }
        }
      };

      const poll = async () => {
        if (closed) return;

        try {
          const job = await jobQueue.getJob(jobId);
          if (!job) {
            sendMessage({ type: "failed", jobId, error: "Job not found" });
            socket.close();
            closed = true;
            return;
          }

          if (job.status === "completed") {
            sendMessage({
              type: "completed",
              jobId,
              progress: 100,
              result: job.result,
            });
            socket.close();
            closed = true;
            return;
          }

          if (job.status === "failed") {
            sendMessage({
              type: "failed",
              jobId,
              error: job.error ?? "Unknown error",
            });
            socket.close();
            closed = true;
            return;
          }

          sendMessage({
            type: "progress",
            jobId,
            progress: job.progress,
          });
        } catch {
          if (!closed) {
            sendMessage({ type: "failed", jobId, error: "Internal error" });
            socket.close();
            closed = true;
          }
        }
      };

      const intervalId = setInterval(poll, 2000);

      // Send initial status immediately
      await poll();

      socket.on("close", () => {
        closed = true;
        clearInterval(intervalId);
      });

      socket.on("error", () => {
        closed = true;
        clearInterval(intervalId);
      });
    }
  );
};

export default jobProgressWs;
