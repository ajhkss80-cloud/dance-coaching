const BASE = "/api";

export const endpoints = {
  generate: `${BASE}/generate`,
  generateStatus: (jobId: string) => `${BASE}/generate/${jobId}`,
  coach: `${BASE}/coach`,
  coachStatus: (jobId: string) => `${BASE}/coach/${jobId}`,
  config: `${BASE}/config`,
  health: `${BASE}/health`,
  file: (filename: string) => `${BASE}/files/${filename}`,
};

export function wsJob(jobId: string): string {
  const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = typeof window !== "undefined" ? window.location.host : "localhost:3001";
  return `${protocol}//${host}/api/ws/jobs/${jobId}`;
}
