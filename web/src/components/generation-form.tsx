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
  const [backend, setBackend] = useState("cloud");
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
    if (jobId) updateJob(jobId, { status: "completed", summary: "Dance generation completed" });
    addToast({ title: "Generation complete", description: "Your dance video is ready!" });
  }
  if (wsStatus === "failed" && state === "processing") {
    setState("failed");
    setErrorMsg(wsError || "Generation failed");
    if (jobId) updateJob(jobId, { status: "failed", summary: wsError || "Failed" });
    addToast({ title: "Generation failed", description: wsError || "An error occurred", variant: "destructive" });
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
      const msg = err instanceof Error ? err.message : "Failed to start generation";
      setErrorMsg(msg);
      addToast({ title: "Error", description: msg, variant: "destructive" });
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
          <CardTitle>Generate Dance Video</CardTitle>
          <CardDescription>
            Upload an avatar image and reference dance video to generate a new dance performance.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <FileUpload
              accept="image/*"
              label="Avatar Image"
              onFileChange={setAvatarImage}
            />
            <FileUpload
              accept="video/*"
              label="Reference Video"
              onFileChange={setReferenceVideo}
            />
          </div>

          <BackendSelector value={backend} onValueChange={setBackend} />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Max Duration</label>
              <span className="text-sm text-muted-foreground">{maxDuration}s</span>
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
              <label className="text-sm font-medium">Segment Length</label>
              <span className="text-sm text-muted-foreground">{segmentLength}s</span>
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
              {state === "uploading" ? "Uploading..." : "Generate"}
            </Button>
            {(state === "completed" || state === "failed") && (
              <Button variant="outline" onClick={handleReset}>
                New Generation
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
