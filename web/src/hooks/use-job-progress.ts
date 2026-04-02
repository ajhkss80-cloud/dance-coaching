"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { wsJob } from "@/lib/api-endpoints";
import type { JobStatus, WsProgressMessage } from "@/types/api";

interface UseJobProgressOptions {
  jobId: string | null;
}

interface UseJobProgressReturn {
  progress: number;
  status: JobStatus | null;
  progressMessage: string;
  result: unknown | null;
  error: string | null;
  isConnected: boolean;
}

export function useJobProgress({ jobId }: UseJobProgressOptions): UseJobProgressReturn {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [progressMessage, setProgressMessage] = useState("");
  const [result, setResult] = useState<unknown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (!jobId) {
      cleanup();
      return;
    }

    function connect() {
      cleanup();

      const url = wsJob(jobId!);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WsProgressMessage;

          if (msg.type === "progress") {
            setProgress(msg.progress ?? 0);
            setProgressMessage(msg.progressMessage ?? "");
            setStatus("active");
          } else if (msg.type === "completed") {
            setProgress(100);
            setStatus("completed");
            setResult(msg.result ?? null);
          } else if (msg.type === "failed") {
            setStatus("failed");
            setError(msg.error ?? "Job failed");
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (status !== "completed" && status !== "failed") {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 10000);
          retryCountRef.current += 1;
          retryTimerRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return cleanup;
  }, [jobId, cleanup, status]);

  return { progress, status, progressMessage, result, error, isConnected };
}
