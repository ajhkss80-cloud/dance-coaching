"use client";

import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

interface BackendSelectorProps {
  value: string;
  onValueChange: (value: string) => void;
}

export function BackendSelector({ value, onValueChange }: BackendSelectorProps) {
  const label = value === "comfyui" ? "Local (ComfyUI)" : "Cloud (WaveSpeed/Kling)";

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Backend</label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger aria-label="Select backend">
          <SelectValue placeholder="Select backend">{label}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="cloud">Cloud (WaveSpeed/Kling)</SelectItem>
          <SelectItem value="comfyui">Local (ComfyUI)</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
