"use client";

import { useState, useCallback } from "react";
import { FileUpload } from "@/components/file-upload";
import { ProgressTracker } from "@/components/progress-tracker";
import { CoachResult } from "@/components/coach-result";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { useJobHistory } from "@/hooks/use-job-history";
import { useJobProgress } from "@/hooks/use-job-progress";
import { api } from "@/lib/api-client";
import { Target } from "lucide-react";
import type { CoachResult as CoachResultType } from "@/types/coach";

type FormState = "idle" | "uploading" | "processing" | "completed" | "failed";

export function CoachForm() {
  const [state, setState] = useState<FormState>("idle");
  const [userVideo, setUserVideo] = useState<File | null>(null);
  const [referenceVideo, setReferenceVideo] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<CoachResultType | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { addToast } = useToast();
  const { addJob, updateJob } = useJobHistory();
  const { status: wsStatus, result: wsResult, error: wsError } = useJobProgress({ jobId });

  if (wsStatus === "completed" && state === "processing" && wsResult) {
    setState("completed");
    setResult(wsResult as CoachResultType);
    if (jobId) updateJob(jobId, { status: "completed", summary: "Coaching analysis completed" });
    addToast({ title: "Analysis complete", description: "Your coaching results are ready!" });
  }
  if (wsStatus === "failed" && state === "processing") {
    setState("failed");
    setErrorMsg(wsError || "Analysis failed");
    if (jobId) updateJob(jobId, { status: "failed", summary: wsError || "Failed" });
    addToast({ title: "Analysis failed", description: wsError || "An error occurred", variant: "destructive" });
  }

  const handleSubmit = useCallback(async () => {
    if (!userVideo || !referenceVideo) return;

    setState("uploading");
    setErrorMsg(null);
    setResult(null);

    try {
      const response = await api.startCoaching({ userVideo, referenceVideo });
      setJobId(response.jobId);
      setState("processing");
      addJob({ jobId: response.jobId, type: "coach", status: "active" });
    } catch (err) {
      setState("failed");
      const msg = err instanceof Error ? err.message : "Failed to start analysis";
      setErrorMsg(msg);
      addToast({ title: "Error", description: msg, variant: "destructive" });
    }
  }, [userVideo, referenceVideo, addJob, addToast]);

  const handleReset = useCallback(() => {
    setState("idle");
    setJobId(null);
    setResult(null);
    setErrorMsg(null);
  }, []);

  const canSubmit = userVideo && referenceVideo && state === "idle";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Dance Coach</CardTitle>
          <CardDescription>
            Upload your dance video and a reference video to get AI-powered coaching feedback.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <FileUpload
              accept="video/*"
              label="Your Dance Video"
              onFileChange={setUserVideo}
            />
            <FileUpload
              accept="video/*"
              label="Reference Video"
              onFileChange={setReferenceVideo}
            />
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="flex-1"
            >
              <Target className="h-4 w-4" aria-hidden="true" />
              {state === "uploading" ? "Uploading..." : "Analyze"}
            </Button>
            {(state === "completed" || state === "failed") && (
              <Button variant="outline" onClick={handleReset}>
                New Analysis
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {(state === "processing" || state === "uploading") && (
        <ProgressTracker jobId={jobId} />
      )}

      {errorMsg && state === "failed" && (
        <Card className="border-destructive">
          <CardContent className="py-4">
            <p className="text-sm text-destructive" role="alert">{errorMsg}</p>
          </CardContent>
        </Card>
      )}

      {result && state === "completed" && <CoachResult result={result} />}
    </div>
  );
}
