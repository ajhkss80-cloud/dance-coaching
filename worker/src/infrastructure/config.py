"""Application configuration loaded from environment variables.

Uses pydantic-settings to provide validated, typed configuration
with sensible defaults. Loads .env files via python-dotenv.
"""
from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class WorkerConfig(BaseSettings):
    """Worker configuration with environment variable binding.

    All settings can be overridden via environment variables or a .env
    file in the project root. Variable names match the field names in
    uppercase (e.g., ``GENERATION_BACKEND``).
    """

    # --- Backend selection ---
    GENERATION_BACKEND: str = "cloud"

    # --- Kling (cloud) backend ---
    KLING_API_KEY: str = ""
    KLING_API_BASE_URL: str = "https://api.klingai.com/v1"

    # --- MimicMotion (local) backend ---
    MIMICMOTION_MODEL_DIR: str = "./models/mimicmotion"
    MIMICMOTION_REPO_DIR: str = "./vendor/MimicMotion"

    # --- Storage ---
    STORAGE_DIR: str = "./storage"

    # --- Segmentation ---
    SEGMENT_MAX_LENGTH_SEC: int = 10
    MAX_VIDEO_DURATION_SEC: int = 180

    # --- Redis / BullMQ ---
    REDIS_URL: str = "redis://localhost:6379"
    WORKER_CONCURRENCY: int = 1

    # --- RIFE interpolation ---
    RIFE_MODEL_DIR: str = "./models/rife"
    RIFE_INTERPOLATION_FRAMES: int = 2

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @field_validator("GENERATION_BACKEND")
    @classmethod
    def _validate_backend(cls, v: str) -> str:
        allowed = {"cloud", "local"}
        normalized = v.strip().lower()
        if normalized not in allowed:
            raise ValueError(
                f"GENERATION_BACKEND must be one of {allowed}, got '{v}'"
            )
        return normalized

    @field_validator("SEGMENT_MAX_LENGTH_SEC")
    @classmethod
    def _validate_segment_length(cls, v: int) -> int:
        if v < 1 or v > 60:
            raise ValueError(
                f"SEGMENT_MAX_LENGTH_SEC must be between 1 and 60, got {v}"
            )
        return v

    @field_validator("MAX_VIDEO_DURATION_SEC")
    @classmethod
    def _validate_max_duration(cls, v: int) -> int:
        if v < 1 or v > 600:
            raise ValueError(
                f"MAX_VIDEO_DURATION_SEC must be between 1 and 600, got {v}"
            )
        return v

    @field_validator("WORKER_CONCURRENCY")
    @classmethod
    def _validate_concurrency(cls, v: int) -> int:
        if v < 1 or v > 32:
            raise ValueError(
                f"WORKER_CONCURRENCY must be between 1 and 32, got {v}"
            )
        return v

    @field_validator("RIFE_INTERPOLATION_FRAMES")
    @classmethod
    def _validate_rife_frames(cls, v: int) -> int:
        if v < 1 or v > 8:
            raise ValueError(
                f"RIFE_INTERPOLATION_FRAMES must be between 1 and 8, got {v}"
            )
        return v

    @model_validator(mode="after")
    def _validate_cloud_requires_api_key(self) -> WorkerConfig:
        if self.GENERATION_BACKEND == "cloud" and not self.KLING_API_KEY:
            raise ValueError(
                "KLING_API_KEY is required when GENERATION_BACKEND is 'cloud'"
            )
        return self
