"""Unit tests for the WorkerConfig."""
from __future__ import annotations

import pytest


class TestWorkerConfig:
    """Tests for configuration validation."""

    def test_cloud_backend_requires_api_key_wavespeed(self) -> None:
        """Cloud + wavespeed raises if WAVESPEED_API_KEY is missing."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="WAVESPEED_API_KEY is required"):
            WorkerConfig(
                GENERATION_BACKEND="cloud",
                CLOUD_PROVIDER="wavespeed",
                WAVESPEED_API_KEY="",
            )

    def test_cloud_backend_requires_api_key_kling(self) -> None:
        """Cloud + kling raises if KLING_API_KEY is missing."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="KLING_API_KEY is required"):
            WorkerConfig(
                GENERATION_BACKEND="cloud",
                CLOUD_PROVIDER="kling",
                KLING_API_KEY="",
            )

    def test_cloud_backend_requires_api_key_falai(self) -> None:
        """Cloud + falai raises if FALAI_API_KEY is missing."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="FALAI_API_KEY is required"):
            WorkerConfig(
                GENERATION_BACKEND="cloud",
                CLOUD_PROVIDER="falai",
                FALAI_API_KEY="",
            )

    def test_cloud_backend_with_wavespeed_key_succeeds(self) -> None:
        """Cloud + wavespeed succeeds when API key is provided."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="wavespeed",
            WAVESPEED_API_KEY="ws-key-123",
        )
        assert config.GENERATION_BACKEND == "cloud"
        assert config.CLOUD_PROVIDER == "wavespeed"
        assert config.WAVESPEED_API_KEY == "ws-key-123"

    def test_cloud_backend_with_kling_key_succeeds(self) -> None:
        """Cloud + kling succeeds when API key is provided."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="kling",
            KLING_API_KEY="kling-key-123",
        )
        assert config.GENERATION_BACKEND == "cloud"
        assert config.CLOUD_PROVIDER == "kling"

    def test_cloud_backend_with_falai_key_succeeds(self) -> None:
        """Cloud + falai succeeds when API key is provided."""
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="falai",
            FALAI_API_KEY="fal-key-123",
        )
        assert config.GENERATION_BACKEND == "cloud"
        assert config.CLOUD_PROVIDER == "falai"

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

    def test_invalid_cloud_provider_rejected(self) -> None:
        """Invalid cloud provider raises ValueError."""
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="CLOUD_PROVIDER"):
            WorkerConfig(
                GENERATION_BACKEND="local",
                CLOUD_PROVIDER="invalid",
            )

    def test_cloud_provider_validation(self) -> None:
        """Cloud provider accepts all valid options."""
        from src.infrastructure.config import WorkerConfig

        for provider in ("wavespeed", "kling", "falai"):
            config = WorkerConfig(
                GENERATION_BACKEND="local",
                CLOUD_PROVIDER=provider,
            )
            assert config.CLOUD_PROVIDER == provider

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
        assert config.CLOUD_PROVIDER == "wavespeed"
        assert config.CLOUD_MODEL == "steady-dancer"
        assert config.WAVESPEED_RESOLUTION == "720p"
        assert config.FALAI_MODEL == "kling-v3-standard-mc"
        assert config.KLING_QUALITY == "720p"
        assert config.KLING_CHARACTER_ORIENTATION == "video"

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

    def test_wavespeed_requires_key_when_selected(self) -> None:
        """WaveSpeed requires key only when it is the active provider."""
        from src.infrastructure.config import WorkerConfig

        # Should NOT raise - wavespeed key not needed when using kling
        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="kling",
            KLING_API_KEY="kling-key",
            WAVESPEED_API_KEY="",
        )
        assert config.CLOUD_PROVIDER == "kling"

    def test_falai_requires_key_when_selected(self) -> None:
        """fal.ai requires key only when it is the active provider."""
        from src.infrastructure.config import WorkerConfig

        # Should NOT raise - falai key not needed when using wavespeed
        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="wavespeed",
            WAVESPEED_API_KEY="ws-key",
            FALAI_API_KEY="",
        )
        assert config.CLOUD_PROVIDER == "wavespeed"
