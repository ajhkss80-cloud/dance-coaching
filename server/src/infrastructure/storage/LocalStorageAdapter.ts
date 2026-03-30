import { mkdir, rm, stat } from "node:fs/promises";
import { createWriteStream } from "node:fs";
import { join, resolve } from "node:path";
import { pipeline } from "node:stream/promises";
import { IStorage } from "../../application/ports/IStorage.js";

export class LocalStorageAdapter implements IStorage {
  private readonly uploadsDir: string;
  private readonly outputsDir: string;

  constructor(baseDir: string) {
    const resolved = resolve(baseDir);
    this.uploadsDir = join(resolved, "uploads");
    this.outputsDir = join(resolved, "outputs");
  }

  async init(): Promise<void> {
    await mkdir(this.uploadsDir, { recursive: true });
    await mkdir(this.outputsDir, { recursive: true });
  }

  async saveFile(
    stream: NodeJS.ReadableStream,
    filename: string,
    jobId: string
  ): Promise<string> {
    await mkdir(this.uploadsDir, { recursive: true });

    const sanitizedFilename = filename.replace(/[^a-zA-Z0-9._-]/g, "_");
    const destFilename = `${jobId}_${sanitizedFilename}`;
    const destPath = join(this.uploadsDir, destFilename);

    const writeStream = createWriteStream(destPath);
    await pipeline(stream, writeStream);

    return destPath;
  }

  getOutputPath(jobId: string, suffix: string): string {
    return join(this.outputsDir, `${jobId}_${suffix}`);
  }

  async fileExists(path: string): Promise<boolean> {
    try {
      const info = await stat(path);
      return info.isFile();
    } catch {
      return false;
    }
  }

  async cleanup(jobId: string): Promise<void> {
    const pattern = `${jobId}_`;

    const { readdir } = await import("node:fs/promises");

    for (const dir of [this.uploadsDir, this.outputsDir]) {
      try {
        const files = await readdir(dir);
        for (const file of files) {
          if (file.startsWith(pattern)) {
            await rm(join(dir, file), { force: true });
          }
        }
      } catch {
        // Directory might not exist, that's fine
      }
    }
  }

  getUploadsDir(): string {
    return this.uploadsDir;
  }

  getOutputsDir(): string {
    return this.outputsDir;
  }
}
