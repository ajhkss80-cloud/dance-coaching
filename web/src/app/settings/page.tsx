"use client";

import { useConfig } from "@/hooks/use-config";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Server, Clock, Layers, Cloud, Monitor, DollarSign } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function SettingsPage() {
  const { data: config, isLoading, error } = useConfig();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>플랫폼 설정</CardTitle>
          <CardDescription>백엔드 서버의 현재 설정 정보입니다.</CardDescription>
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
              설정을 불러올 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.
            </p>
          ) : config ? (
            <>
              <div className="flex items-center gap-4 rounded-lg border border-border p-4">
                <Server className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm font-medium">영상 생성 백엔드</p>
                  <p className="text-sm text-muted-foreground">{config.generationBackend}</p>
                </div>
                <Badge variant="secondary">
                  {config.generationBackend?.includes("comfyui") ? "로컬" : "클라우드"}
                </Badge>
              </div>

              <Separator />

              <div className="flex items-center gap-4 rounded-lg border border-border p-4">
                <Clock className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm font-medium">최대 영상 길이</p>
                  <p className="text-sm text-muted-foreground">{config.maxVideoDurationSec}초</p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-4 rounded-lg border border-border p-4">
                <Layers className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm font-medium">세그먼트 최대 길이</p>
                  <p className="text-sm text-muted-foreground">{config.segmentMaxLengthSec}초</p>
                </div>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      {/* Cloud Provider Pricing */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cloud className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <CardTitle>클라우드 제공업체 비교</CardTitle>
          </div>
          <CardDescription>API 기반 영상 생성 서비스 가격 및 특징 비교</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" aria-label="클라우드 제공업체 비교">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">제공업체</th>
                  <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">가격</th>
                  <th className="pb-3 text-left font-medium text-muted-foreground">특징</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border">
                  <td className="py-3 pr-4 font-medium">
                    WaveSpeed SteadyDancer
                    <Badge variant="secondary" className="ml-2 text-[10px]">추천</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">$0.04~0.08/초</td>
                  <td className="py-3 text-muted-foreground">얼굴 일관성 최고</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="py-3 pr-4 font-medium">WaveSpeed Wan 2.2</td>
                  <td className="py-3 pr-4 text-muted-foreground">$0.04~0.08/초</td>
                  <td className="py-3 text-muted-foreground">댄스 타이밍 최고</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="py-3 pr-4 font-medium">Kling 3.0 EvoLink</td>
                  <td className="py-3 pr-4 text-muted-foreground">$0.075/초</td>
                  <td className="py-3 text-muted-foreground">안무 정확도 최고</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">
                    fal.ai
                    <Badge variant="outline" className="ml-2 text-[10px]">백업</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">$0.168/초</td>
                  <td className="py-3 text-muted-foreground">Failover용</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Local Provider Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Monitor className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <CardTitle>로컬 모델 (ComfyUI)</CardTitle>
          </div>
          <CardDescription>GPU를 사용하여 직접 실행하는 로컬 모델 비교</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" aria-label="로컬 모델 비교">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">모델</th>
                  <th className="pb-3 pr-4 text-left font-medium text-muted-foreground">가격</th>
                  <th className="pb-3 text-left font-medium text-muted-foreground">특징</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border">
                  <td className="py-3 pr-4 font-medium">
                    SteadyDancer
                    <Badge variant="secondary" className="ml-2 text-[10px]">추천</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">무료 (GPU 필요)</td>
                  <td className="py-3 text-muted-foreground">품질 최고</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="py-3 pr-4 font-medium">SCAIL</td>
                  <td className="py-3 pr-4 text-muted-foreground">무료 (GPU 필요)</td>
                  <td className="py-3 text-muted-foreground">멀티캐릭터 지원</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="py-3 pr-4 font-medium">Wan 2.2 Animate</td>
                  <td className="py-3 pr-4 text-muted-foreground">무료 (GPU 필요)</td>
                  <td className="py-3 text-muted-foreground">범용 최강</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">
                    MimicMotion
                    <Badge variant="outline" className="ml-2 text-[10px]">레거시</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">무료 (GPU 필요)</td>
                  <td className="py-3 text-muted-foreground">레거시 지원</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>플랫폼 정보</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            AI 댄스 코칭 플랫폼 - AI 기반 댄스 영상 생성 및 코칭 피드백 시스템입니다.
            모든 기능을 사용하려면 백엔드 API 서버(localhost:3000)를 실행해주세요.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
