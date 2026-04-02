"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "dance-coaching-history";

export interface HistoryEntry {
  id: string;
  jobId: string;
  type: "generate" | "coach";
  status: "queued" | "active" | "completed" | "failed";
  createdAt: string;
  summary?: string;
}

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function useJobHistory() {
  const [jobs, setJobs] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setJobs(loadHistory());
  }, []);

  const addJob = useCallback(
    (entry: Omit<HistoryEntry, "id" | "createdAt">) => {
      const newEntry: HistoryEntry = {
        ...entry,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        createdAt: new Date().toISOString(),
      };
      setJobs((prev) => {
        const next = [newEntry, ...prev].slice(0, 100);
        saveHistory(next);
        return next;
      });
      return newEntry;
    },
    []
  );

  const updateJob = useCallback(
    (jobId: string, updates: Partial<Pick<HistoryEntry, "status" | "summary">>) => {
      setJobs((prev) => {
        const next = prev.map((j) => (j.jobId === jobId ? { ...j, ...updates } : j));
        saveHistory(next);
        return next;
      });
    },
    []
  );

  const getJobs = useCallback(() => {
    return loadHistory();
  }, []);

  const clearHistory = useCallback(() => {
    setJobs([]);
    saveHistory([]);
  }, []);

  return { jobs, addJob, updateJob, getJobs, clearHistory };
}
