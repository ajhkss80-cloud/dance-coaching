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
    if (jobId) updateJob(jobId, { status: "completed", summary: "코칭 분석 완료" });
    addToast({ title: "분석 완료", description: "코칭 결과가 준비되었습니다!" });
  }
  if (wsStatus === "failed" && state === "processing") {
    setState("failed");
    setErrorMsg(wsError || "분석 실패");
    if (jobId) updateJob(jobId, { status: "failed", summary: wsError || "실패" });
    addToast({ title: "분석 실패", description: wsError || "오류가 발생했습니다", variant: "destructive" });
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
      const msg = err instanceof Error ? err.message : "분석을 시작할 수 없습니다";
      setErrorMsg(msg);
      addToast({ title: "오류", description: msg, variant: "destructive" });
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
          <CardTitle>댄스 코칭</CardTitle>
          <CardDescription>
            내 댄스 영상과 레퍼런스 영상을 업로드하여 AI 코칭 피드백을 받으세요.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <FileUpload
              accept="video/*"
              label="내 댄스 영상"
              onFileChange={setUserVideo}
            />
            <FileUpload
              accept="video/*"
              label="레퍼런스 영상"
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
              {state === "uploading" ? "업로드 중..." : "분석 시작"}
            </Button>
            {(state === "completed" || state === "failed") && (
              <Button variant="outline" onClick={handleReset}>
                새로 분석
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
