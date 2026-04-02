"use client";

import { cn } from "@/lib/utils";
import { endpoints } from "@/lib/api-endpoints";

interface VideoPlayerProps {
  src: string;
  className?: string;
  poster?: string;
}

export function VideoPlayer({ src, className, poster }: VideoPlayerProps) {
  const fullSrc = src.startsWith("/api/files/")
    ? src
    : src.startsWith("http")
      ? src
      : endpoints.file(src);

  return (
    <div className={cn("overflow-hidden rounded-lg bg-black", className)}>
      <video
        src={fullSrc}
        controls
        className="h-full w-full"
        poster={poster}
        preload="metadata"
      >
        <track kind="captions" />
        Your browser does not support the video element.
      </video>
    </div>
  );
}
