import { cn } from "@/lib/utils";

interface FeedbackCardProps {
  index: number;
  feedback: string;
  className?: string;
}

export function FeedbackCard({ index, feedback, className }: FeedbackCardProps) {
  return (
    <div className={cn("flex items-start gap-3 rounded-lg border border-border bg-card p-4", className)}>
      <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
        {index + 1}
      </div>
      <p className="text-sm leading-relaxed">{feedback}</p>
    </div>
  );
}
