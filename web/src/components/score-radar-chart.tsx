"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

interface ScoreRadarChartProps {
  jointScores: Record<string, number>;
  className?: string;
}

const JOINT_LABELS: Record<string, string> = {
  left_arm: "왼팔",
  right_arm: "오른팔",
  left_leg: "왼다리",
  right_leg: "오른다리",
  torso: "몸통",
  head: "머리",
  leftArm: "왼팔",
  rightArm: "오른팔",
  leftLeg: "왼다리",
  rightLeg: "오른다리",
};

export function ScoreRadarChart({ jointScores, className }: ScoreRadarChartProps) {
  const data = Object.entries(jointScores).map(([key, value]) => ({
    joint: JOINT_LABELS[key] || key,
    score: Math.round(value),
  }));

  const avgScore = data.length > 0
    ? data.reduce((sum, d) => sum + d.score, 0) / data.length
    : 0;

  const color = avgScore >= 80 ? "#22c55e" : avgScore >= 60 ? "#eab308" : "#ef4444";

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="80%">
          <PolarGrid stroke="var(--color-border, #e5e7eb)" />
          <PolarAngleAxis
            dataKey="joint"
            tick={{ fill: "var(--color-foreground, #171717)", fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: "var(--color-muted-foreground, #737373)", fontSize: 10 }}
          />
          <Radar
            name="점수"
            dataKey="score"
            stroke={color}
            fill={color}
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
