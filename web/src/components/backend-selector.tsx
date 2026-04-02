"use client";

import { useState } from "react";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Cloud, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";

interface BackendSelectorProps {
  value: string;
  onValueChange: (value: string) => void;
}

const CLOUD_PROVIDERS = [
  {
    value: "wavespeed-steadydancer",
    label: "WaveSpeed SteadyDancer",
    price: "$0.04~0.08/초",
    description: "얼굴 일관성 최고",
    badge: "추천",
  },
  {
    value: "wavespeed-wan22",
    label: "WaveSpeed Wan 2.2",
    price: "$0.04~0.08/초",
    description: "댄스 타이밍 최고",
  },
  {
    value: "kling-evolink",
    label: "Kling 3.0 EvoLink",
    price: "$0.075/초",
    description: "안무 정확도 최고",
  },
  {
    value: "fal-ai",
    label: "fal.ai",
    price: "$0.168/초",
    description: "Failover용",
    badge: "백업",
  },
];

const LOCAL_PROVIDERS = [
  {
    value: "comfyui-steadydancer",
    label: "SteadyDancer",
    description: "품질 최고",
    badge: "추천",
  },
  {
    value: "comfyui-scail",
    label: "SCAIL",
    description: "멀티캐릭터 지원",
  },
  {
    value: "comfyui-wan22",
    label: "Wan 2.2 Animate",
    description: "범용 최강",
  },
  {
    value: "comfyui-mimicmotion",
    label: "MimicMotion",
    description: "레거시",
    badge: "레거시",
  },
];

export function BackendSelector({ value, onValueChange }: BackendSelectorProps) {
  const isCloud = !value.startsWith("comfyui");
  const [mode, setMode] = useState<"cloud" | "local">(isCloud ? "cloud" : "local");

  const providers = mode === "cloud" ? CLOUD_PROVIDERS : LOCAL_PROVIDERS;
  const currentProvider = providers.find((p) => p.value === value) || providers[0];

  function handleModeChange(newMode: string) {
    const m = newMode as "cloud" | "local";
    setMode(m);
    const defaultVal = m === "cloud" ? CLOUD_PROVIDERS[0].value : LOCAL_PROVIDERS[0].value;
    onValueChange(defaultVal);
  }

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium">백엔드 선택</label>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => handleModeChange("cloud")}
          className={cn(
            "flex items-center gap-2 rounded-lg border-2 p-3 text-left text-sm font-medium transition-colors",
            mode === "cloud"
              ? "border-primary bg-primary/5 text-primary"
              : "border-border text-muted-foreground hover:border-primary/50"
          )}
        >
          <Cloud className="h-4 w-4" aria-hidden="true" />
          <div>
            <div>클라우드</div>
            <div className="text-xs font-normal text-muted-foreground">API 기반 생성</div>
          </div>
        </button>
        <button
          type="button"
          onClick={() => handleModeChange("local")}
          className={cn(
            "flex items-center gap-2 rounded-lg border-2 p-3 text-left text-sm font-medium transition-colors",
            mode === "local"
              ? "border-primary bg-primary/5 text-primary"
              : "border-border text-muted-foreground hover:border-primary/50"
          )}
        >
          <Monitor className="h-4 w-4" aria-hidden="true" />
          <div>
            <div>로컬 (ComfyUI)</div>
            <div className="text-xs font-normal text-muted-foreground">GPU 직접 실행</div>
          </div>
        </button>
      </div>

      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger aria-label="모델 선택">
          <SelectValue placeholder="모델을 선택하세요">{currentProvider.label}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {providers.map((p) => (
            <SelectItem key={p.value} value={p.value}>
              <div className="flex items-center gap-2">
                <span>{p.label}</span>
                {"price" in p && (
                  <span className="text-xs text-muted-foreground">{(p as typeof CLOUD_PROVIDERS[number]).price}</span>
                )}
                {p.badge && (
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {p.badge}
                  </Badge>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Card className="bg-muted/50">
        <CardContent className="p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{currentProvider.label}</span>
            {"price" in currentProvider && (
              <span className="text-muted-foreground">{(currentProvider as typeof CLOUD_PROVIDERS[number]).price}</span>
            )}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{currentProvider.description}</p>
        </CardContent>
      </Card>
    </div>
  );
}
