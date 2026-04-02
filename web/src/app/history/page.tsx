"use client";

import { useJobHistory } from "@/hooks/use-job-history";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { JobStatusBadge } from "@/components/job-status-badge";
import { Trash2, Wand2, Target, Inbox } from "lucide-react";
import type { JobStatus } from "@/types/api";

export default function HistoryPage() {
  const { jobs, clearHistory } = useJobHistory();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>작업 기록</CardTitle>
            {jobs.length > 0 && (
              <Button variant="outline" size="sm" onClick={clearHistory}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                기록 삭제
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden="true" />
              <p className="text-lg font-medium">작업 기록이 없습니다</p>
              <p className="text-sm text-muted-foreground">
                영상 생성이나 코칭을 시작하면 여기에 기록이 표시됩니다.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" aria-label="작업 기록">
                <thead>
                  <tr className="border-b border-border">
                    <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">유형</th>
                    <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">작업 ID</th>
                    <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">상태</th>
                    <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">날짜</th>
                    <th className="pb-3 text-left font-medium text-muted-foreground">요약</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.id} className="border-b border-border last:border-0">
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          {job.type === "generate" ? (
                            <Wand2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                          ) : (
                            <Target className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                          )}
                          <span>{job.type === "generate" ? "영상 생성" : "댄스 코칭"}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <code className="text-xs">{job.jobId.slice(0, 8)}...</code>
                      </td>
                      <td className="py-3 pr-4">
                        <JobStatusBadge status={job.status as JobStatus} />
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">
                        {new Date(job.createdAt).toLocaleDateString("ko-KR")}
                      </td>
                      <td className="py-3 text-muted-foreground">
                        {job.summary || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
