"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreRadarChart } from "@/components/score-radar-chart";
import { FeedbackCard } from "@/components/feedback-card";
import { formatScore } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { CoachResult as CoachResultType } from "@/types/coach";

interface CoachResultProps {
  result: CoachResultType;
}

export function CoachResult({ result }: CoachResultProps) {
  const scoreColor =
    result.overallScore >= 80
      ? "text-green-600 dark:text-green-400"
      : result.overallScore >= 60
        ? "text-yellow-600 dark:text-yellow-400"
        : "text-red-600 dark:text-red-400";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Overall Score</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center">
          <div className={cn("text-6xl font-bold tabular-nums", scoreColor)}>
            {formatScore(result.overallScore)}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {result.overallScore >= 80
              ? "Great performance!"
              : result.overallScore >= 60
                ? "Good effort, keep practicing!"
                : "Keep working at it!"}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Joint Scores</CardTitle>
        </CardHeader>
        <CardContent>
          <ScoreRadarChart jointScores={result.jointScores} />
        </CardContent>
      </Card>

      {result.feedback.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Feedback</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.feedback.map((item, i) => (
              <FeedbackCard key={i} index={i} feedback={item} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
