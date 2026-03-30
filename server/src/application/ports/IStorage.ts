export interface IStorage {
  saveFile(
    stream: NodeJS.ReadableStream,
    filename: string,
    jobId: string
  ): Promise<string>;

  getOutputPath(jobId: string, suffix: string): string;

  fileExists(path: string): Promise<boolean>;

  cleanup(jobId: string): Promise<void>;
}
