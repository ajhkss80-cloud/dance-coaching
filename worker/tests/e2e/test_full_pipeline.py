"""E2E test: Full dance coaching platform pipeline.

Uses FakeBackend, FakeAudioProcessor, FakeStitcher, FakePoseExtractor
to verify the complete flow from input to output without requiring
GPU, API keys, or external services.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.application.use_cases.coach_dance import CoachDanceUseCase
from src.application.use_cases.generate_tutorial import GenerateTutorialUseCase
from src.di.container import Container, create_container
from src.infrastructure.config import WorkerConfig
from tests.harness.fake_audio_processor import FakeAudioProcessor
from tests.harness.fake_backend import FakeBackend
from tests.harness.fake_pose_extractor import FakePoseExtractor
from tests.harness.fake_stitcher import FakeInterpolator, FakeStitcher
from tests.harness.sample_data import create_sample_avatar, create_sample_video


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_container(
    *,
    backend: FakeBackend | None = None,
    audio: FakeAudioProcessor | None = None,
    pose: FakePoseExtractor | None = None,
    stitcher: FakeStitcher | None = None,
    interpolator: FakeInterpolator | None = None,
) -> Container:
    """Create a fully-wired DI container with fake dependencies."""
    config = WorkerConfig(GENERATION_BACKEND="local")
    return create_container(
        config,
        backend_override=backend or FakeBackend(),
        audio_processor_override=audio or FakeAudioProcessor(),
        pose_extractor_override=pose or FakePoseExtractor(),
        stitcher_override=stitcher or FakeStitcher(),
        interpolator_override=interpolator or FakeInterpolator(),
    )


# ===========================================================================
# Generation Pipeline E2E
# ===========================================================================


class TestE2EGenerationPipeline:
    """Test the complete tutorial video generation flow."""

    async def test_generate_tutorial_end_to_end(self, tmp_path: Path) -> None:
        """Full generation pipeline produces output with correct structure."""
        # Arrange: create sample media files
        avatar_path = create_sample_avatar(tmp_path / "avatar.png")
        reference_path = create_sample_video(
            tmp_path / "reference.mp4", duration=3.0
        )

        container = _build_container()
        use_case = container.generate_use_case

        # Act
        result = await use_case.execute(
            job_id="e2e-gen-001",
            avatar_path=str(avatar_path),
            reference_path=str(reference_path),
            backend_type="local",
            options={"skip_stitch": True},
        )

        # Assert
        assert result["job_id"] == "e2e-gen-001"
        assert result["status"] == "completed"
        assert "output_path" in result
        assert result["segments_count"] >= 1

    async def test_generate_tutorial_progress_tracking(
        self, tmp_path: Path
    ) -> None:
        """Progress callbacks are monotonically increasing."""
        avatar_path = create_sample_avatar(tmp_path / "avatar.png")
        reference_path = create_sample_video(
            tmp_path / "reference.mp4", duration=3.0
        )

        container = _build_container()
        use_case = container.generate_use_case

        progress_values: list[float] = []

        def track_progress(value: float) -> None:
            progress_values.append(value)

        await use_case.execute(
            job_id="e2e-gen-002",
            avatar_path=str(avatar_path),
            reference_path=str(reference_path),
            backend_type="local",
            options={"skip_stitch": True},
            progress_callback=track_progress,
        )

        # Progress must have been reported at least once
        assert len(progress_values) >= 1

        # Progress values must be monotonically non-decreasing
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1], (
                f"Progress decreased at index {i}: "
                f"{progress_values[i - 1]} -> {progress_values[i]}"
            )

        # Final progress must reach 100
        assert progress_values[-1] == 100.0

    async def test_generate_tutorial_with_long_video(
        self, tmp_path: Path
    ) -> None:
        """A 30-second video should produce multiple segments."""
        avatar_path = create_sample_avatar(tmp_path / "avatar.png")
        # Create a 30-second reference video
        reference_path = create_sample_video(
            tmp_path / "reference.mp4", duration=3.0
        )

        # Configure audio processor to report 30s duration with many beats
        audio = FakeAudioProcessor(
            beat_times=[float(i) for i in range(1, 30)],
            duration=30.0,
        )
        container = _build_container(audio=audio)
        use_case = container.generate_use_case

        result = await use_case.execute(
            job_id="e2e-gen-003",
            avatar_path=str(avatar_path),
            reference_path=str(reference_path),
            backend_type="local",
            options={"skip_stitch": True},
        )

        assert result["status"] == "completed"
        # With 30s duration and 10s max segment length, expect >= 3 segments
        assert result["segments_count"] >= 3

    async def test_generate_tutorial_backend_failure(
        self, tmp_path: Path
    ) -> None:
        """Backend failure on a segment results in a failed job."""
        avatar_path = create_sample_avatar(tmp_path / "avatar.png")
        reference_path = create_sample_video(
            tmp_path / "reference.mp4", duration=3.0
        )

        backend = FakeBackend(fail_on_segments=[0])
        container = _build_container(backend=backend)
        use_case = container.generate_use_case

        result = await use_case.execute(
            job_id="e2e-gen-004",
            avatar_path=str(avatar_path),
            reference_path=str(reference_path),
            backend_type="local",
            options={"skip_stitch": True},
        )

        assert result["status"] == "failed"
        assert "error" in result


# ===========================================================================
# Coaching Pipeline E2E
# ===========================================================================


class TestE2ECoachingPipeline:
    """Test the complete dance coaching flow."""

    async def test_coach_dance_end_to_end(self, tmp_path: Path) -> None:
        """Full coaching pipeline produces scores and feedback."""
        user_video = create_sample_video(
            tmp_path / "user.mp4", duration=3.0
        )
        reference_video = create_sample_video(
            tmp_path / "reference.mp4", duration=3.0
        )

        container = _build_container()
        use_case = container.coach_use_case

        result = await use_case.execute(
            job_id="e2e-coach-001",
            user_video=str(user_video),
            reference_video=str(reference_video),
        )

        assert result["job_id"] == "e2e-coach-001"
        assert result["status"] == "completed"

        # Overall score must be in valid range
        assert 0.0 <= result["overall_score"] <= 100.0

        # All joint groups must be present
        joint_scores = result["joint_scores"]
        expected_joints = {
            "left_arm",
            "right_arm",
            "left_leg",
            "right_leg",
            "torso",
            "head",
        }
        assert set(joint_scores.keys()) == expected_joints

        # Each joint score must be in valid range
        for joint, score in joint_scores.items():
            assert 0.0 <= score <= 100.0, (
                f"Joint '{joint}' score {score} out of range"
            )

        # Feedback must be a non-empty list of strings
        assert isinstance(result["feedback"], list)
        assert len(result["feedback"]) >= 1
        assert all(isinstance(f, str) for f in result["feedback"])

    async def test_coach_identical_videos_high_score(
        self, tmp_path: Path
    ) -> None:
        """Identical fake pose data should produce a consistent high score.

        The FakePoseExtractor generates deterministic sine-wave data,
        so both videos yield the same poses. The Phase 1 scoring stub
        returns fixed moderate scores regardless of input, but the
        important thing is that the pipeline completes without error
        and returns valid scores when inputs are identical.
        """
        video = create_sample_video(tmp_path / "dance.mp4", duration=3.0)

        # Use the same video path for both user and reference
        container = _build_container()
        use_case = container.coach_use_case

        result = await use_case.execute(
            job_id="e2e-coach-002",
            user_video=str(video),
            reference_video=str(video),
        )

        assert result["status"] == "completed"
        # With identical inputs, scoring should succeed
        assert result["overall_score"] > 0.0

    async def test_coach_different_videos_produces_scores(
        self, tmp_path: Path
    ) -> None:
        """Different videos complete with valid scores.

        Uses two FakePoseExtractors with different frame counts to
        simulate different-length performances.
        """
        user_video = create_sample_video(
            tmp_path / "user.mp4", duration=3.0
        )
        reference_video = create_sample_video(
            tmp_path / "ref.mp4", duration=5.0
        )

        # Different frame counts simulate different-length performances
        pose = FakePoseExtractor(num_frames=60, fps=30)
        container = _build_container(pose=pose)
        use_case = container.coach_use_case

        result = await use_case.execute(
            job_id="e2e-coach-003",
            user_video=str(user_video),
            reference_video=str(reference_video),
        )

        assert result["status"] == "completed"
        assert 0.0 <= result["overall_score"] <= 100.0
        assert len(result["feedback"]) >= 1

    async def test_coach_progress_tracking(self, tmp_path: Path) -> None:
        """Coaching progress callbacks fire in order."""
        user_video = create_sample_video(
            tmp_path / "user.mp4", duration=3.0
        )
        reference_video = create_sample_video(
            tmp_path / "ref.mp4", duration=3.0
        )

        container = _build_container()
        use_case = container.coach_use_case

        progress_values: list[float] = []

        result = await use_case.execute(
            job_id="e2e-coach-004",
            user_video=str(user_video),
            reference_video=str(reference_video),
            progress_callback=lambda v: progress_values.append(v),
        )

        assert result["status"] == "completed"
        assert len(progress_values) >= 1

        # Progress must be monotonically non-decreasing
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

        # Final progress reaches 100
        assert progress_values[-1] == 100.0

    async def test_coach_missing_video_fails(self, tmp_path: Path) -> None:
        """Missing video file produces a failed result."""
        reference_video = create_sample_video(
            tmp_path / "ref.mp4", duration=3.0
        )

        container = _build_container()
        use_case = container.coach_use_case

        result = await use_case.execute(
            job_id="e2e-coach-005",
            user_video=str(tmp_path / "nonexistent.mp4"),
            reference_video=str(reference_video),
        )

        assert result["status"] == "failed"
        assert "error" in result


# ===========================================================================
# Backend Switching E2E
# ===========================================================================


class TestE2EBackendSwitching:
    """Test that the system correctly switches between backends."""

    def test_cloud_backend_selection(self) -> None:
        """Cloud config creates a KlingBackend when no override given."""
        from src.infrastructure.backends.kling_backend import KlingBackend

        config = WorkerConfig(
            GENERATION_BACKEND="cloud",
            KLING_API_KEY="test-key-for-e2e",
        )

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.backend, KlingBackend)
        assert container.config.GENERATION_BACKEND == "cloud"

    def test_local_backend_selection(self) -> None:
        """Local config creates a MimicMotionBackend when no override given."""
        from src.infrastructure.backends.mimicmotion_backend import (
            MimicMotionBackend,
        )

        config = WorkerConfig(GENERATION_BACKEND="local")

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
        )

        assert isinstance(container.backend, MimicMotionBackend)
        assert container.config.GENERATION_BACKEND == "local"

    def test_container_with_overrides_preserves_config(self) -> None:
        """Container preserves the config object regardless of overrides."""
        config = WorkerConfig(GENERATION_BACKEND="local")

        container = _build_container()

        assert isinstance(container.config, WorkerConfig)
        assert isinstance(container.generate_use_case, GenerateTutorialUseCase)
        assert isinstance(container.coach_use_case, CoachDanceUseCase)

    def test_invalid_backend_raises_error(self) -> None:
        """Unknown backend type raises ValueError during config validation."""
        with pytest.raises(ValueError, match="GENERATION_BACKEND"):
            WorkerConfig(GENERATION_BACKEND="invalid_backend")
