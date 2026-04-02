import { ApiError, type JobCreatedResponse } from "@/types/api";
import type { GenerateFormData, GenerateJobStatus } from "@/types/generate";
import type { CoachFormData, CoachJobStatus } from "@/types/coach";
import type { AppConfig } from "@/types/config";
import { endpoints } from "./api-endpoints";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, res.statusText, text || undefined);
  }
  return res.json() as Promise<T>;
}

function buildFormData(data: Record<string, File | string | number>): FormData {
  const fd = new FormData();
  for (const [key, value] of Object.entries(data)) {
    if (value instanceof File) {
      fd.append(key, value);
    } else {
      fd.append(key, String(value));
    }
  }
  return fd;
}

export const api = {
  startGeneration(data: GenerateFormData): Promise<JobCreatedResponse> {
    const fd = buildFormData({
      avatarImage: data.avatarImage,
      referenceVideo: data.referenceVideo,
      backend: data.backend,
      maxDuration: data.maxDuration,
      segmentLength: data.segmentLength,
    });
    return fetchJson<JobCreatedResponse>(endpoints.generate, {
      method: "POST",
      body: fd,
    });
  },

  getGenerateStatus(jobId: string): Promise<GenerateJobStatus> {
    return fetchJson<GenerateJobStatus>(endpoints.generateStatus(jobId));
  },

  startCoaching(data: CoachFormData): Promise<JobCreatedResponse> {
    const fd = buildFormData({
      userVideo: data.userVideo,
      referenceVideo: data.referenceVideo,
    });
    return fetchJson<JobCreatedResponse>(endpoints.coach, {
      method: "POST",
      body: fd,
    });
  },

  getCoachStatus(jobId: string): Promise<CoachJobStatus> {
    return fetchJson<CoachJobStatus>(endpoints.coachStatus(jobId));
  },

  getConfig(): Promise<AppConfig> {
    return fetchJson<AppConfig>(endpoints.config);
  },

  getHealth(): Promise<{ status: string; timestamp: string }> {
    return fetchJson<{ status: string; timestamp: string }>(endpoints.health);
  },
};
