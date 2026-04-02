"use client";

import Link from "next/link";
import { Wand2, Target, Clock, Server, Cloud, Monitor } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useJobHistory } from "@/hooks/use-job-history";
import { useConfig } from "@/hooks/use-config";
import { JobStatusBadge } from "@/components/job-status-badge";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { JobStatus } from "@/types/api";

export default function DashboardPage() {
  const { jobs } = useJobHistory();
  const { data: config } = useConfig();
  const recentJobs = jobs.slice(0, 5);

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 30000,
    retry: false,
  });

  const isHealthy = health?.status === "ok";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>AI 댄스 코칭 플랫폼에 오신 것을 환영합니다</CardTitle>
          <CardDescription>
            AI 기반 댄스 영상 생성과 코칭 피드백으로 댄스 실력을 향상시키세요.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Server status + Backend info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                isHealthy ? "bg-green-100 dark:bg-green-900" : "bg-red-100 dark:bg-red-900"
              )}
            >
              <Server
                className={cn("h-5 w-5", isHealthy ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400")}
                aria-hidden="true"
              />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">서버 연결 상태</p>
              {isHealthy ? (
                <p className="text-sm text-green-600 dark:text-green-400">서버 연결됨</p>
              ) : (
                <p className="text-sm text-red-600 dark:text-red-400">
                  서버 연결 안됨 - API 서버를 실행해주세요
                </p>
              )}
            </div>
            <Badge variant={isHealthy ? "secondary" : "destructive"}>
              {isHealthy ? "온라인" : "오프라인"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              {config?.generationBackend?.includes("comfyui") ? (
                <Monitor className="h-5 w-5 text-primary" aria-hidden="true" />
              ) : (
                <Cloud className="h-5 w-5 text-primary" aria-hidden="true" />
              )}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">현재 백엔드</p>
              <p className="text-sm text-muted-foreground">
                {config?.generationBackend || "설정되지 않음"}
              </p>
            </div>
            <Badge variant="secondary">
              {config?.generationBackend?.includes("comfyui") ? "로컬" : "클라우드"}
            </Badge>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="transition-shadow hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Wand2 className="h-5 w-5 text-primary" aria-hidden="true" />
              </div>
              <div>
                <CardTitle className="text-lg">댄스 영상 생성</CardTitle>
                <CardDescription>아바타와 레퍼런스로 AI 댄스 영상 생성</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Link href="/generate">
              <Button className="w-full">
                <Wand2 className="h-4 w-4" aria-hidden="true" />
                생성 시작하기
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="transition-shadow hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Target className="h-5 w-5 text-primary" aria-hidden="true" />
              </div>
              <div>
                <CardTitle className="text-lg">댄스 코칭</CardTitle>
                <CardDescription>AI 코칭으로 댄스 테크닉 분석 받기</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Link href="/coach">
              <Button className="w-full" variant="secondary">
                <Target className="h-4 w-4" aria-hidden="true" />
                코칭 시작하기
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {recentJobs.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">최근 활동</CardTitle>
              <Link href="/history">
                <Button variant="ghost" size="sm">
                  <Clock className="h-4 w-4" aria-hidden="true" />
                  전체 보기
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between rounded-lg border border-border p-3"
                >
                  <div className="flex items-center gap-3">
                    {job.type === "generate" ? (
                      <Wand2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    ) : (
                      <Target className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    )}
                    <div>
                      <p className="text-sm font-medium">
                        {job.type === "generate" ? "영상 생성" : "댄스 코칭"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(job.createdAt).toLocaleString("ko-KR")}
                      </p>
                    </div>
                  </div>
                  <JobStatusBadge status={job.status as JobStatus} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
