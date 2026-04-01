"""Unit tests for the DI container."""
from __future__ import annotations

import pytest

from src.application.orchestrator import GenerationOrchestrator
from src.application.use_cases.coach_dance import CoachDanceUseCase
from src.application.use_cases.generate_tutorial import GenerateTutorialUseCase
from src.di.container import Container, create_container
from src.infrastructure.config import WorkerConfig
from tests.harness.fake_audio_processor import FakeAudioProcessor
from tests.harness.fake_backend import FakeBackend
from tests.harness.fake_pose_extractor import FakePoseExtractor
from tests.harness.fake_stitcher import FakeInterpolator, FakeStitcher


class TestContainer:
    """Tests for dependency injection container creation."""

    def test_create_container_with_overrides(self) -> None:
        """Container can be created with all dependencies overridden."""
        config = WorkerConfig(
            GENERATION_BACKEND="local",
        )
        backend = FakeBackend()
        audio = FakeAudioProcessor()
        pose = FakePoseExtractor()
        stitcher = FakeStitcher()
        interpolator = FakeInterpolator()

        container = create_container(
            config,
            backend_override=backend,
            audio_processor_override=audio,
            pose_extractor_override=pose,
            stitcher_override=stitcher,
            interpolator_override=interpolator,
        )

        assert isinstance(container, Container)
        assert container.backend is backend
        assert container.audio_processor is audio
        assert container.pose_extractor is pose
        assert container.stitcher is stitcher
        assert container.interpolator is interpolator
        assert isinstance(container.orchestrator, GenerationOrchestrator)
        assert isinstance(container.generate_use_case, GenerateTutorialUseCase)
        assert isinstance(container.coach_use_case, CoachDanceUseCase)

    def test_create_container_cloud_wavespeed_backend(self) -> None:
        """Cloud + wavespeed creates a WaveSpeedBackend."""
        from src.infrastructure.backends.wavespeed_backend import (
            WaveSpeedBackend,
        )

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="wavespeed",
            WAVESPEED_API_KEY="ws-key-123",
            CLOUD_MODEL="steady-dancer",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.backend, WaveSpeedBackend)
        assert container.backend.name() == "wavespeed-steady-dancer"

    def test_create_container_cloud_kling_backend(self) -> None:
        """Cloud + kling creates a KlingBackend."""
        from src.infrastructure.backends.kling_backend import KlingBackend

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="kling",
            KLING_API_KEY="kling-key-123",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.backend, KlingBackend)
        assert container.backend.name() == "kling-evolink"

    def test_create_container_cloud_falai_backend(self) -> None:
        """Cloud + falai creates a FalAIBackend."""
        from src.infrastructure.backends.falai_backend import FalAIBackend

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="falai",
            FALAI_API_KEY="fal-key-123",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.backend, FalAIBackend)
        assert container.backend.name() == "falai-kling-v3-standard-mc"

    def test_create_container_local_backend(self) -> None:
        """Local config creates a MimicMotionBackend when no override given."""
        from src.infrastructure.backends.mimicmotion_backend import (
            MimicMotionBackend,
        )

        config = WorkerConfig(
            GENERATION_BACKEND="local",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.backend, MimicMotionBackend)

    def test_container_config_preserved(self) -> None:
        """Container stores the original config object."""
        config = WorkerConfig(
            GENERATION_BACKEND="local",
        )

        container = create_container(
            config,
            backend_override=FakeBackend(),
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert container.config is config

    def test_container_use_cases_wired_correctly(self) -> None:
        """Use cases receive the correct dependencies."""
        config = WorkerConfig(GENERATION_BACKEND="local")
        backend = FakeBackend()
        audio = FakeAudioProcessor()
        pose = FakePoseExtractor()

        container = create_container(
            config,
            backend_override=backend,
            audio_processor_override=audio,
            pose_extractor_override=pose,
        )

        # The orchestrator should use the injected backend and audio processor
        assert container.orchestrator._backend is backend
        assert container.orchestrator._audio_processor is audio

        # The coach use case should use the injected pose extractor
        assert container.coach_use_case._pose_extractor is pose

    def test_container_creates_default_stitcher(self) -> None:
        """Container creates FFmpegStitcher when no override given."""
        from src.infrastructure.stitch.ffmpeg_stitcher import FFmpegStitcher

        config = WorkerConfig(GENERATION_BACKEND="local")

        container = create_container(
            config,
            backend_override=FakeBackend(),
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.stitcher, FFmpegStitcher)

    def test_container_creates_default_interpolator(self) -> None:
        """Container creates RIFEInterpolator when no override given."""
        from src.infrastructure.stitch.rife_interpolator import RIFEInterpolator

        config = WorkerConfig(GENERATION_BACKEND="local")

        container = create_container(
            config,
            backend_override=FakeBackend(),
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.interpolator, RIFEInterpolator)

    def test_container_orchestrator_has_stitcher(self) -> None:
        """Orchestrator receives the stitcher dependency."""
        config = WorkerConfig(GENERATION_BACKEND="local")
        stitcher = FakeStitcher()
        interpolator = FakeInterpolator()

        container = create_container(
            config,
            backend_override=FakeBackend(),
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
            stitcher_override=stitcher,
            interpolator_override=interpolator,
        )

        assert container.orchestrator._stitcher is stitcher
        assert container.orchestrator._interpolator is interpolator

    def test_cloud_wavespeed_backend_selection(self) -> None:
        """Cloud + wavespeed config selects WaveSpeedBackend."""
        from src.infrastructure.backends.wavespeed_backend import (
            WaveSpeedBackend,
        )

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="wavespeed",
            WAVESPEED_API_KEY="ws-key",
            CLOUD_MODEL="wan-animate",
            WAVESPEED_RESOLUTION="480p",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
            stitcher_override=FakeStitcher(),
            interpolator_override=FakeInterpolator(),
        )

        assert isinstance(container.backend, WaveSpeedBackend)
        assert container.backend.name() == "wavespeed-wan-animate"

    def test_cloud_kling_backend_selection(self) -> None:
        """Cloud + kling config selects KlingBackend."""
        from src.infrastructure.backends.kling_backend import KlingBackend

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="kling",
            KLING_API_KEY="kling-key",
            KLING_QUALITY="1080p",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
            stitcher_override=FakeStitcher(),
            interpolator_override=FakeInterpolator(),
        )

        assert isinstance(container.backend, KlingBackend)
        assert container.backend._quality == "1080p"

    def test_cloud_falai_backend_selection(self) -> None:
        """Cloud + falai config selects FalAIBackend."""
        from src.infrastructure.backends.falai_backend import FalAIBackend

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            CLOUD_PROVIDER="falai",
            FALAI_API_KEY="fal-key",
            FALAI_MODEL="wan-animate",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
            stitcher_override=FakeStitcher(),
            interpolator_override=FakeInterpolator(),
        )

        assert isinstance(container.backend, FalAIBackend)
        assert container.backend.name() == "falai-wan-animate"
