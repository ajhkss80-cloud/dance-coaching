"use client";

import { VideoPlayer } from "@/components/video-player";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, Clock, Layers, Server } from "lucide-react";
import { formatDuration } from "@/lib/utils";
import { endpoints } from "@/lib/api-endpoints";
import type { GenerateResult } from "@/types/generate";

interface GenerationResultProps {
  result: GenerateResult;
}

export function GenerationResult({ result }: GenerationResultProps) {
  const videoSrc = result.outputUrl.startsWith("http")
    ? result.outputUrl
    : endpoints.file(result.outputUrl);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Generation Complete</span>
          <Badge variant="secondary" className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
            Success
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <VideoPlayer src={videoSrc} className="aspect-video w-full" />

        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span>{formatDuration(result.duration)}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Layers className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span>{result.segmentCount} segments</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Server className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span>{result.backend}</span>
          </div>
        </div>

        <a href={videoSrc} download className="block">
          <Button variant="outline" className="w-full">
            <Download className="h-4 w-4" aria-hidden="true" />
            Download Video
          </Button>
        </a>
      </CardContent>
    </Card>
  );
}
