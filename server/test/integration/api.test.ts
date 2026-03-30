import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import Fastify, { FastifyInstance } from "fastify";
import multipart from "@fastify/multipart";
import { Readable } from "node:stream";
import { createContainer, Container } from "../../src/di/container.js";
import { TestJobQueue } from "../harness/TestJobQueue.js";
import { TestStorage } from "../harness/TestStorage.js";
import generateRoutes from "../../src/interface/http/routes/generate.route.js";
import coachRoutes from "../../src/interface/http/routes/coach.route.js";
import configRoutes from "../../src/interface/http/routes/config.route.js";

function buildMultipartBody(
  fields: Record<string, string>,
  files: Record<string, { filename: string; content: Buffer }>
): { body: Buffer; contentType: string } {
  const boundary = "----TestBoundary" + Date.now();
  const parts: Buffer[] = [];

  for (const [name, value] of Object.entries(fields)) {
    parts.push(
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`
      )
    );
  }

  for (const [name, file] of Object.entries(files)) {
    parts.push(
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="${name}"; filename="${file.filename}"\r\nContent-Type: application/octet-stream\r\n\r\n`
      )
    );
    parts.push(file.content);
    parts.push(Buffer.from("\r\n"));
  }

  parts.push(Buffer.from(`--${boundary}--\r\n`));

  return {
    body: Buffer.concat(parts),
    contentType: `multipart/form-data; boundary=${boundary}`,
  };
}

describe("API Integration Tests", () => {
  let app: FastifyInstance;
  let container: Container;
  let testQueue: TestJobQueue;
  let testStorage: TestStorage;

  beforeAll(async () => {
    testQueue = new TestJobQueue();
    testStorage = new TestStorage();

    container = createContainer(
      {
        GENERATION_BACKEND: "local",
        STORAGE_DIR: "./test-storage",
      },
      {
        jobQueue: testQueue,
        storage: testStorage,
      }
    );

    app = Fastify();
    await app.register(multipart, {
      limits: { fileSize: 10 * 1024 * 1024 },
    });
    await app.register(generateRoutes, { container });
    await app.register(coachRoutes, { container });
    await app.register(configRoutes, { container });
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => {
    testQueue.clear();
    testStorage.clear();
  });

  describe("POST /api/generate", () => {
    it("should create a generation job and return 201 with jobId", async () => {
      const { body, contentType } = buildMultipartBody(
        { backend: "local" },
        {
          avatarImage: {
            filename: "avatar.png",
            content: Buffer.from("fake-avatar-data"),
          },
          referenceVideo: {
            filename: "reference.mp4",
            content: Buffer.from("fake-reference-data"),
          },
        }
      );

      const response = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: {
          "content-type": contentType,
        },
      });

      expect(response.statusCode).toBe(201);
      const json = response.json();
      expect(json.jobId).toBeDefined();
      expect(typeof json.jobId).toBe("string");
      expect(json.message).toBe("Generation job created");
    });

    it("should store files via storage adapter", async () => {
      const { body, contentType } = buildMultipartBody(
        {},
        {
          avatarImage: {
            filename: "avatar.png",
            content: Buffer.from("avatar-content"),
          },
          referenceVideo: {
            filename: "ref.mp4",
            content: Buffer.from("reference-content"),
          },
        }
      );

      const response = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: {
          "content-type": contentType,
        },
      });

      expect(response.statusCode).toBe(201);
      expect(testStorage.getFileCount()).toBe(2);
    });

    it("should enqueue with correct payload type", async () => {
      const { body, contentType } = buildMultipartBody(
        { backend: "local" },
        {
          avatarImage: {
            filename: "avatar.png",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "ref.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const response = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: { "content-type": contentType },
      });

      const json = response.json();
      const payload = testQueue.getStoredPayload(json.jobId);
      expect(payload).toBeDefined();
      expect(payload!.type).toBe("generate");
      expect(payload!.data.backend).toBe("local");
    });
  });

  describe("GET /api/generate/:jobId", () => {
    it("should return job status for existing job", async () => {
      // Create a job first
      const { body, contentType } = buildMultipartBody(
        { backend: "local" },
        {
          avatarImage: {
            filename: "avatar.png",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "ref.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const createResponse = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: { "content-type": contentType },
      });

      const { jobId } = createResponse.json();

      const statusResponse = await app.inject({
        method: "GET",
        url: `/api/generate/${jobId}`,
      });

      expect(statusResponse.statusCode).toBe(200);
      const json = statusResponse.json();
      expect(json.jobId).toBe(jobId);
      expect(json.status).toBe("queued");
      expect(json.progress).toBe(0);
    });

    it("should return 404 for non-existent job", async () => {
      const response = await app.inject({
        method: "GET",
        url: "/api/generate/nonexistent-id",
      });

      expect(response.statusCode).toBe(404);
      const json = response.json();
      expect(json.error).toContain("not found");
    });

    it("should reflect progress updates", async () => {
      const { body, contentType } = buildMultipartBody(
        { backend: "local" },
        {
          avatarImage: {
            filename: "a.png",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "r.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const createRes = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: { "content-type": contentType },
      });

      const { jobId } = createRes.json();
      testQueue.simulateProgress(jobId, 50);

      const statusRes = await app.inject({
        method: "GET",
        url: `/api/generate/${jobId}`,
      });

      expect(statusRes.statusCode).toBe(200);
      const json = statusRes.json();
      expect(json.status).toBe("active");
      expect(json.progress).toBe(50);
    });

    it("should return completed status with result", async () => {
      const { body, contentType } = buildMultipartBody(
        { backend: "local" },
        {
          avatarImage: {
            filename: "a.png",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "r.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const createRes = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: { "content-type": contentType },
      });

      const { jobId } = createRes.json();
      testQueue.simulateCompletion(jobId, {
        outputUrl: "/api/files/output.mp4",
        duration: 30,
        segmentCount: 3,
        backend: "local",
      });

      const statusRes = await app.inject({
        method: "GET",
        url: `/api/generate/${jobId}`,
      });

      expect(statusRes.statusCode).toBe(200);
      const json = statusRes.json();
      expect(json.status).toBe("completed");
      expect(json.progress).toBe(100);
      expect(json.result).toBeDefined();
      expect(json.result.outputUrl).toBe("/api/files/output.mp4");
    });

    it("should return failed status with error", async () => {
      const { body, contentType } = buildMultipartBody(
        { backend: "local" },
        {
          avatarImage: {
            filename: "a.png",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "r.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const createRes = await app.inject({
        method: "POST",
        url: "/api/generate",
        payload: body,
        headers: { "content-type": contentType },
      });

      const { jobId } = createRes.json();
      testQueue.simulateFailure(jobId, "Backend processing error");

      const statusRes = await app.inject({
        method: "GET",
        url: `/api/generate/${jobId}`,
      });

      expect(statusRes.statusCode).toBe(200);
      const json = statusRes.json();
      expect(json.status).toBe("failed");
      expect(json.error).toBe("Backend processing error");
    });
  });

  describe("POST /api/coach", () => {
    it("should create a coaching job and return 201", async () => {
      const { body, contentType } = buildMultipartBody(
        {},
        {
          userVideo: {
            filename: "user.mp4",
            content: Buffer.from("user-video-data"),
          },
          referenceVideo: {
            filename: "reference.mp4",
            content: Buffer.from("reference-data"),
          },
        }
      );

      const response = await app.inject({
        method: "POST",
        url: "/api/coach",
        payload: body,
        headers: { "content-type": contentType },
      });

      expect(response.statusCode).toBe(201);
      const json = response.json();
      expect(json.jobId).toBeDefined();
      expect(json.message).toBe("Coaching job created");
    });

    it("should enqueue with coach type", async () => {
      const { body, contentType } = buildMultipartBody(
        {},
        {
          userVideo: {
            filename: "user.mp4",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "ref.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const response = await app.inject({
        method: "POST",
        url: "/api/coach",
        payload: body,
        headers: { "content-type": contentType },
      });

      const json = response.json();
      const payload = testQueue.getStoredPayload(json.jobId);
      expect(payload).toBeDefined();
      expect(payload!.type).toBe("coach");
    });
  });

  describe("GET /api/coach/:jobId", () => {
    it("should return coaching job status", async () => {
      const { body, contentType } = buildMultipartBody(
        {},
        {
          userVideo: {
            filename: "user.mp4",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "ref.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const createRes = await app.inject({
        method: "POST",
        url: "/api/coach",
        payload: body,
        headers: { "content-type": contentType },
      });

      const { jobId } = createRes.json();

      const statusRes = await app.inject({
        method: "GET",
        url: `/api/coach/${jobId}`,
      });

      expect(statusRes.statusCode).toBe(200);
      const json = statusRes.json();
      expect(json.jobId).toBe(jobId);
      expect(json.status).toBe("queued");
    });

    it("should return 404 for non-existent coaching job", async () => {
      const response = await app.inject({
        method: "GET",
        url: "/api/coach/nonexistent-id",
      });

      expect(response.statusCode).toBe(404);
    });

    it("should return completed coaching result", async () => {
      const { body, contentType } = buildMultipartBody(
        {},
        {
          userVideo: {
            filename: "user.mp4",
            content: Buffer.from("data"),
          },
          referenceVideo: {
            filename: "ref.mp4",
            content: Buffer.from("data"),
          },
        }
      );

      const createRes = await app.inject({
        method: "POST",
        url: "/api/coach",
        payload: body,
        headers: { "content-type": contentType },
      });

      const { jobId } = createRes.json();
      testQueue.simulateCompletion(jobId, {
        overallScore: 85,
        jointScores: { shoulder: 90, hip: 80 },
        feedback: ["Good shoulder movement", "Improve hip rotation"],
      });

      const statusRes = await app.inject({
        method: "GET",
        url: `/api/coach/${jobId}`,
      });

      expect(statusRes.statusCode).toBe(200);
      const json = statusRes.json();
      expect(json.status).toBe("completed");
      expect(json.result).toBeDefined();
      expect(json.result.overallScore).toBe(85);
      expect(json.result.feedback).toHaveLength(2);
    });
  });

  describe("GET /api/config", () => {
    it("should return current backend configuration", async () => {
      const response = await app.inject({
        method: "GET",
        url: "/api/config",
      });

      expect(response.statusCode).toBe(200);
      const json = response.json();
      expect(json.generationBackend).toBe("local");
      expect(json.maxVideoDurationSec).toBe(180);
      expect(json.segmentMaxLengthSec).toBe(10);
    });
  });
});
