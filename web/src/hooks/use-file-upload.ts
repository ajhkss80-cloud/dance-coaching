"use client";

import { useState, useCallback, useRef, useEffect } from "react";

interface UseFileUploadOptions {
  accept?: string;
  maxSizeMB?: number;
}

interface UseFileUploadReturn {
  file: File | null;
  preview: string | null;
  error: string | null;
  isDragging: boolean;
  handleDrop: (e: React.DragEvent) => void;
  handleDragOver: (e: React.DragEvent) => void;
  handleDragEnter: (e: React.DragEvent) => void;
  handleDragLeave: (e: React.DragEvent) => void;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  reset: () => void;
}

export function useFileUpload(options: UseFileUploadOptions = {}): UseFileUploadReturn {
  const { accept, maxSizeMB = 500 } = options;
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const previewUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
      }
    };
  }, []);

  const validateFile = useCallback(
    (f: File): boolean => {
      if (accept) {
        const types = accept.split(",").map((t) => t.trim());
        const matches = types.some((t) => {
          if (t.endsWith("/*")) {
            return f.type.startsWith(t.replace("/*", "/"));
          }
          return f.type === t;
        });
        if (!matches) {
          setError(`Invalid file type. Expected: ${accept}`);
          return false;
        }
      }
      if (f.size > maxSizeMB * 1024 * 1024) {
        setError(`File too large. Max size: ${maxSizeMB}MB`);
        return false;
      }
      return true;
    },
    [accept, maxSizeMB]
  );

  const processFile = useCallback(
    (f: File) => {
      if (!validateFile(f)) return;

      setError(null);
      setFile(f);

      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
      }

      const url = URL.createObjectURL(f);
      previewUrlRef.current = url;
      setPreview(url);
    },
    [validateFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) processFile(f);
    },
    [processFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) processFile(f);
    },
    [processFile]
  );

  const reset = useCallback(() => {
    setFile(null);
    setError(null);
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setPreview(null);
  }, []);

  return {
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
  };
}
