"""Unit tests for the WorkerConfig."""
from __future__ import annotations

import pytest


class TestWorkerConfig:
    """Tests for configuration validation."""

    def test_cloud_backend_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cloud backend raises if KLING_API_KEY is missing."""
        from src.infrastructure.config import WorkerConfig

        monkeypatch.delenv("KLING_API_KEY", raising=False)
        monkeypatch.setenv("GENERATION_BACKEND", "cloud")

        with pytest.raises(ValueError, match="KLING_API_KEY is required"):
            WorkerConfig(GENERATION_BACKEND="cloud", KLING_API_KEY="")

    def test_cloud_backend_with_key_succeeds(self) -> None:
        """Cloud backend succeeds when API key is provided."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            KLING_API_KEY="test-key-123",
        )
        assert config.GENERATION_BACKEND == "cloud"
        assert config.KLING_API_KEY == "test-key-123"

    def test_local_backend_no_key_required(self) -> None:
        """Local backend does not require an API key."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="local",
            KLING_API_KEY="",
        )
        assert config.GENERATION_BACKEND == "local"

    def test_invalid_backend_type_rejected(self) -> None:
        """Invalid backend type raises ValueError."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="GENERATION_BACKEND"):
            WorkerConfig(GENERATION_BACKEND="invalid")

    def test_backend_normalisation(self) -> None:
        """Backend type is normalised to lowercase."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="LOCAL",
        )
        assert config.GENERATION_BACKEND == "local"

    def test_default_values(self) -> None:
        """Default values are applied for optional settings."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="local",
        )
        assert config.SEGMENT_MAX_LENGTH_SEC == 10
        assert config.MAX_VIDEO_DURATION_SEC == 180
        assert config.WORKER_CONCURRENCY == 1
        assert config.RIFE_INTERPOLATION_FRAMES == 2
        assert config.REDIS_URL == "redis://localhost:6379"
        assert config.STORAGE_DIR == "./storage"

    def test_segment_length_validation(self) -> None:
        """Segment length outside 1-60 is rejected."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="SEGMENT_MAX_LENGTH_SEC"):
            WorkerConfig(
                GENERATION_BACKEND="local",
                SEGMENT_MAX_LENGTH_SEC=0,
            )

    def test_concurrency_validation(self) -> None:
        """Concurrency outside 1-32 is rejected."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="WORKER_CONCURRENCY"):
            WorkerConfig(
                GENERATION_BACKEND="local",
                WORKER_CONCURRENCY=0,
            )
