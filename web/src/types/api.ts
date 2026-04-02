export class ApiError extends Error {
  status: number;
  statusText: string;

  constructor(status: number, statusText: string, message?: string) {
    super(message || `API Error: ${status} ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
  }
}

export type JobStatus = "queued" | "active" | "completed" | "failed";

export interface JobCreatedResponse {
  jobId: string;
  message: string;
}

export interface WsProgressMessage {
  type: "progress" | "completed" | "failed";
  jobId: string;
  progress?: number;
  progressMessage?: string;
  result?: unknown;
  error?: string;
}
