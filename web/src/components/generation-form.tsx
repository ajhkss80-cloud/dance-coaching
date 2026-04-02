"use client";

import { useState, useCallback } from "react";
import { FileUpload } from "@/components/file-upload";
import { BackendSelector } from "@/components/backend-selector";
import { ProgressTracker } from "@/components/progress-tracker";
import { GenerationResult } from "@/components/generation-result";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { useJobHistory } from "@/hooks/use-job-history";
import { useJobProgress } from "@/hooks/use-job-progress";
import { api } from "@/lib/api-client";
import { Wand2 } from "lucide-react";
import type { GenerateResult } from "@/types/generate";

type FormState = "idle" | "uploading" | "processing" | "completed" | "failed";

export function GenerationForm() {
  const [state, setState] = useState<FormState>("idle");
  const [avatarImage, setAvatarImage] = useState<File | null>(null);
  const [referenceVideo, setReferenceVideo] = useState<File | null>(null);
  const [backend, setBackend] = useState("wavespeed-steadydancer");
  const [maxDuration, setMaxDuration] = useState(10);
  const [segmentLength, setSegmentLength] = useState(5);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { addToast } = useToast();
  const { addJob, updateJob } = useJobHistory();
  const { status: wsStatus, result: wsResult, error: wsError } = useJobProgress({ jobId });

  // Sync WS updates to form state
  if (wsStatus === "completed" && state === "processing" && wsResult) {
    setState("completed");
    setResult(wsResult as GenerateResult);
    if (jobId) updateJob(jobId, { status: "completed", summary: "댄스 영상 생성 완료" });
    addToast({ title: "생성 완료", description: "댄스 영상이 준비되었습니다!" });
  }
  if (wsStatus === "failed" && state === "processing") {
    setState("failed");
    setErrorMsg(wsError || "생성 실패");
    if (jobId) updateJob(jobId, { status: "failed", summary: wsError || "실패" });
    addToast({ title: "생성 실패", description: wsError || "오류가 발생했습니다", variant: "destructive" });
  }

  const handleSubmit = useCallback(async () => {
    if (!avatarImage || !referenceVideo) return;

    setState("uploading");
    setErrorMsg(null);
    setResult(null);

    try {
      const response = await api.startGeneration({
        avatarImage,
        referenceVideo,
        backend,
        maxDuration,
        segmentLength,
      });

      setJobId(response.jobId);
      setState("processing");
      addJob({ jobId: response.jobId, type: "generate", status: "active" });
    } catch (err) {
      setState("failed");
      const msg = err instanceof Error ? err.message : "생성을 시작할 수 없습니다";
      setErrorMsg(msg);
      addToast({ title: "오류", description: msg, variant: "destructive" });
    }
  }, [avatarImage, referenceVideo, backend, maxDuration, segmentLength, addJob, addToast]);

  const handleReset = useCallback(() => {
    setState("idle");
    setJobId(null);
    setResult(null);
    setErrorMsg(null);
  }, []);

  const canSubmit = avatarImage && referenceVideo && state === "idle";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>댄스 영상 생성</CardTitle>
          <CardDescription>
            아바타 이미지와 레퍼런스 댄스 영상을 업로드하여 새로운 댄스 퍼포먼스를 생성합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <FileUpload
              accept="image/*"
              label="아바타 이미지"
              onFileChange={setAvatarImage}
            />
            <FileUpload
              accept="video/*"
              label="레퍼런스 영상"
              onFileChange={setReferenceVideo}
            />
          </div>

          <BackendSelector value={backend} onValueChange={setBackend} />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">최대 길이</label>
              <span className="text-sm text-muted-foreground">{maxDuration}초</span>
            </div>
            <Slider
              min={1}
              max={60}
              step={1}
              value={maxDuration}
              onValueChange={setMaxDuration}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">세그먼트 길이</label>
              <span className="text-sm text-muted-foreground">{segmentLength}초</span>
            </div>
            <Slider
              min={1}
              max={30}
              step={1}
              value={segmentLength}
              onValueChange={setSegmentLength}
            />
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="flex-1"
            >
              <Wand2 className="h-4 w-4" aria-hidden="true" />
              {state === "uploading" ? "업로드 중..." : "생성 시작"}
            </Button>
            {(state === "completed" || state === "failed") && (
              <Button variant="outline" onClick={handleReset}>
                새로 생성
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

      {result && state === "completed" && (
        <GenerationResult result={result} />
      )}
    </div>
  );
}
