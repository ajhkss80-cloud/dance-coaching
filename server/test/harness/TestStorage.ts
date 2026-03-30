import { IStorage } from "../../src/application/ports/IStorage.js";

export class TestStorage implements IStorage {
  private files = new Map<string, Buffer>();
  private outputPaths = new Map<string, string>();

  async saveFile(
    stream: NodeJS.ReadableStream,
    filename: string,
    jobId: string
  ): Promise<string> {
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    const path = `/storage/uploads/${jobId}_${filename}`;
    this.files.set(path, Buffer.concat(chunks));
    return path;
  }

  getOutputPath(jobId: string, suffix: string): string {
    const path = `/storage/outputs/${jobId}_${suffix}`;
    this.outputPaths.set(path, path);
    return path;
  }

  async fileExists(path: string): Promise<boolean> {
    return this.files.has(path);
  }

  async cleanup(jobId: string): Promise<void> {
    for (const key of this.files.keys()) {
      if (key.includes(jobId)) {
        this.files.delete(key);
      }
    }
    for (const key of this.outputPaths.keys()) {
      if (key.includes(jobId)) {
        this.outputPaths.delete(key);
      }
    }
  }

  // Test helpers

  addFile(path: string, content: Buffer = Buffer.from("test")): void {
    this.files.set(path, content);
  }

  getFile(path: string): Buffer | undefined {
    return this.files.get(path);
  }

  getFileCount(): number {
    return this.files.size;
  }

  clear(): void {
    this.files.clear();
    this.outputPaths.clear();
  }
}
