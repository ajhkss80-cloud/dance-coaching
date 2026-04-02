"use client";

import Link from "next/link";
import { Wand2, Target, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useJobHistory } from "@/hooks/use-job-history";
import { JobStatusBadge } from "@/components/job-status-badge";
import type { JobStatus } from "@/types/api";

export default function DashboardPage() {
  const { jobs } = useJobHistory();
  const recentJobs = jobs.slice(0, 5);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Welcome to Dance Coaching Platform</CardTitle>
          <CardDescription>
            Generate AI-powered dance videos and get coaching feedback on your performances.
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="transition-shadow hover:shadow-md">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Wand2 className="h-5 w-5 text-primary" aria-hidden="true" />
              </div>
              <div>
                <CardTitle className="text-lg">Generate Dance</CardTitle>
                <CardDescription>Create AI dance videos from an avatar and reference</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Link href="/generate">
              <Button className="w-full">
                <Wand2 className="h-4 w-4" aria-hidden="true" />
                Start Generating
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
                <CardTitle className="text-lg">Dance Coach</CardTitle>
                <CardDescription>Get AI feedback on your dance technique</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Link href="/coach">
              <Button className="w-full" variant="secondary">
                <Target className="h-4 w-4" aria-hidden="true" />
                Start Coaching
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {recentJobs.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Recent Activity</CardTitle>
              <Link href="/history">
                <Button variant="ghost" size="sm">
                  <Clock className="h-4 w-4" aria-hidden="true" />
                  View All
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
                      <p className="text-sm font-medium capitalize">{job.type}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(job.createdAt).toLocaleString()}
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
