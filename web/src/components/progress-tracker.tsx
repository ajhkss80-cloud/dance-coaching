"use client";

import { useJobProgress } from "@/hooks/use-job-progress";
import { Progress } from "@/components/ui/progress";
import { JobStatusBadge } from "@/components/job-status-badge";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProgressTrackerProps {
  jobId: string | null;
  className?: string;
}

export function ProgressTracker({ jobId, className }: ProgressTrackerProps) {
  const { progress, status, progressMessage, error } = useJobProgress({ jobId });

  if (!jobId) return null;

  return (
    <div className={cn("space-y-4 rounded-lg border border-border bg-card p-6", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {status === "active" && (
            <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
          )}
          <span className="text-sm font-medium">
            {status === "active" ? "처리 중..." : status === "queued" ? "대기 중..." : "작업 상태"}
          </span>
        </div>
        {status && <JobStatusBadge status={status} />}
      </div>

      <Progress value={progress} />

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{progressMessage || "대기 중..."}</span>
        <span>{Math.round(progress)}%</span>
      </div>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          오류: {error}
        </p>
      )}
    </div>
  );
}
