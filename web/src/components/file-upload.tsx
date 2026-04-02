"use client";

import { useRef } from "react";
import { Upload, X, FileVideo, Image } from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import { useFileUpload } from "@/hooks/use-file-upload";
import { Button } from "@/components/ui/button";

interface FileUploadProps {
  accept: string;
  label: string;
  onFileChange: (file: File | null) => void;
  className?: string;
}

export function FileUpload({ accept, label, onFileChange, className }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const {
    file,
    preview,
    error,
    isDragging,
    handleDrop,
    handleDragOver,
    handleDragEnter,
    handleDragLeave,
    handleFileSelect,
    reset,
  } = useFileUpload({ accept });

  const isImage = accept.includes("image");
  const FileIcon = isImage ? Image : FileVideo;

  function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    handleFileSelect(e);
    const f = e.target.files?.[0];
    if (f) onFileChange(f);
  }

  function onDrop(e: React.DragEvent) {
    handleDrop(e);
    const f = e.dataTransfer.files[0];
    if (f) onFileChange(f);
  }

  function onRemove() {
    reset();
    onFileChange(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  if (file && preview) {
    return (
      <div className={cn("relative rounded-lg border border-border bg-card p-4", className)}>
        <div className="flex items-start gap-4">
          <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded-md bg-muted">
            {isImage ? (
              <img src={preview} alt="Preview" className="h-full w-full object-cover" />
            ) : (
              <video src={preview} className="h-full w-full object-cover" muted />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onRemove} aria-label="Remove file">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      <label className="text-sm font-medium">{label}</label>
      <div
        className={cn(
          "relative flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors",
          isDragging
            ? "border-primary bg-primary/5 ring-2 ring-primary/20"
            : "border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/50",
          error && "border-destructive"
        )}
        onDrop={onDrop}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label={`Upload ${label}`}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={onSelect}
          className="sr-only"
          aria-label={label}
        />
        <FileIcon className="mb-2 h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium">
          {isDragging ? "Drop file here" : "Click or drag to upload"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {isImage ? "PNG, JPG, WebP" : "MP4, WebM, MOV"}
        </p>
      </div>
      {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
    </div>
  );
}
