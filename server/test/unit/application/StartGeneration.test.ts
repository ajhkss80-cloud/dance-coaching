import { describe, it, expect, vi, beforeEach } from "vitest";
import { StartGeneration } from "../../../src/application/use-cases/StartGeneration.js";
import { IJobQueue, JobPayload } from "../../../src/application/ports/IJobQueue.js";
import { IStorage } from "../../../src/application/ports/IStorage.js";
import { ValidationError } from "../../../src/domain/errors/DomainError.js";
import { Job } from "../../../src/domain/entities/Job.js";

function createMockJobQueue(): IJobQueue {
  return {
    enqueue: vi.fn(async (_payload: JobPayload) => "job-123"),
    getJob: vi.fn(async (_id: string) => null as Job | null),
    getProgress: vi.fn(async (_id: string) => 0),
  };
}

function createMockStorage(): IStorage {
  return {
    saveFile: vi.fn(async () => "/uploads/file.mp4"),
    getOutputPath: vi.fn(() => "/output/job-123/result.mp4"),
    fileExists: vi.fn(async () => true),
    cleanup: vi.fn(async () => undefined),
  };
}

describe("StartGeneration Use Case", () => {
  let jobQueue: IJobQueue;
  let storage: IStorage;
  let useCase: StartGeneration;

  beforeEach(() => {
    jobQueue = createMockJobQueue();
    storage = createMockStorage();
    useCase = new StartGeneration(jobQueue, storage);
  });

  it("should enqueue a generation job and return jobId", async () => {
    const jobId = await useCase.execute({
      avatarPath: "/uploads/avatar.png",
      referencePath: "/uploads/reference.mp4",
    });

    expect(jobId).toBe("job-123");
    expect(jobQueue.enqueue).toHaveBeenCalledOnce();
    expect(jobQueue.enqueue).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "generate",
        data: expect.objectContaining({
          avatarPath: "/uploads/avatar.png",
          referencePath: "/uploads/reference.mp4",
          backend: "cloud",
          maxDuration: 60,
          segmentLength: 10,
        }),
      })
    );
  });

  it("should use provided backend option", async () => {
    await useCase.execute({
      avatarPath: "/uploads/avatar.png",
      referencePath: "/uploads/reference.mp4",
      backend: "local",
    });

    expect(jobQueue.enqueue).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          backend: "local",
        }),
      })
    );
  });

  it("should use custom maxDuration and segmentLength", async () => {
    await useCase.execute({
      avatarPath: "/uploads/avatar.png",
      referencePath: "/uploads/reference.mp4",
      maxDuration: 120,
      segmentLength: 15,
    });

    expect(jobQueue.enqueue).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          maxDuration: 120,
          segmentLength: 15,
        }),
      })
    );
  });

  it("should default backend to cloud", async () => {
    await useCase.execute({
      avatarPath: "/uploads/avatar.png",
      referencePath: "/uploads/reference.mp4",
    });

    expect(jobQueue.enqueue).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ backend: "cloud" }),
      })
    );
  });

  it("should throw ValidationError for empty avatarPath", async () => {
    await expect(
      useCase.execute({
        avatarPath: "",
        referencePath: "/uploads/reference.mp4",
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should throw ValidationError for empty referencePath", async () => {
    await expect(
      useCase.execute({
        avatarPath: "/uploads/avatar.png",
        referencePath: "",
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should throw ValidationError for invalid backend", async () => {
    await expect(
      useCase.execute({
        avatarPath: "/uploads/avatar.png",
        referencePath: "/uploads/reference.mp4",
        backend: "quantum",
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should throw ValidationError for invalid maxDuration", async () => {
    await expect(
      useCase.execute({
        avatarPath: "/uploads/avatar.png",
        referencePath: "/uploads/reference.mp4",
        maxDuration: 500,
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should throw ValidationError for invalid segmentLength", async () => {
    await expect(
      useCase.execute({
        avatarPath: "/uploads/avatar.png",
        referencePath: "/uploads/reference.mp4",
        segmentLength: 1,
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should throw ValidationError when avatar file does not exist", async () => {
    vi.mocked(storage.fileExists).mockImplementation(async (path: string) => {
      return path !== "/uploads/avatar.png";
    });

    await expect(
      useCase.execute({
        avatarPath: "/uploads/avatar.png",
        referencePath: "/uploads/reference.mp4",
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should throw ValidationError when reference file does not exist", async () => {
    vi.mocked(storage.fileExists).mockImplementation(async (path: string) => {
      return path !== "/uploads/reference.mp4";
    });

    await expect(
      useCase.execute({
        avatarPath: "/uploads/avatar.png",
        referencePath: "/uploads/reference.mp4",
      })
    ).rejects.toThrow(ValidationError);
  });

  it("should check file existence before enqueuing", async () => {
    await useCase.execute({
      avatarPath: "/uploads/avatar.png",
      referencePath: "/uploads/reference.mp4",
    });

    expect(storage.fileExists).toHaveBeenCalledTimes(2);
    expect(storage.fileExists).toHaveBeenCalledWith("/uploads/avatar.png");
    expect(storage.fileExists).toHaveBeenCalledWith("/uploads/reference.mp4");
  });
});
