"use client";

import { useConfig } from "@/hooks/use-config";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Server, Clock, Layers } from "lucide-react";

export default function SettingsPage() {
  const { data: config, isLoading, error } = useConfig();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>Current platform settings from the backend server.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : error ? (
            <p className="text-sm text-destructive" role="alert">
              Failed to load configuration. Make sure the backend is running.
            </p>
          ) : config ? (
            <>
              <div className="flex items-center gap-4 rounded-lg border border-border p-4">
                <Server className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Generation Backend</p>
                  <p className="text-sm text-muted-foreground">{config.generationBackend}</p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-4 rounded-lg border border-border p-4">
                <Clock className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Max Video Duration</p>
                  <p className="text-sm text-muted-foreground">{config.maxVideoDurationSec} seconds</p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-4 rounded-lg border border-border p-4">
                <Layers className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Segment Max Length</p>
                  <p className="text-sm text-muted-foreground">{config.segmentMaxLengthSec} seconds</p>
                </div>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Dance Coaching Platform - AI-powered dance video generation and coaching feedback.
            Connect your backend API server at localhost:3000 to use all features.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
