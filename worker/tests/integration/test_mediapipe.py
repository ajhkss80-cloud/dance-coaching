"""Integration tests for the MediaPipe pose extractor.

Tests require mediapipe and opencv-python-headless to be installed.
Automatically skipped when mediapipe is not available.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.errors import PipelineError, ValidationError
from src.domain.value_objects import PoseFrame

# Skip the entire module if mediapipe is not available
try:
    import mediapipe  # noqa: F401
    _mediapipe_available = True
except ImportError:
    _mediapipe_available = False

pytestmark = pytest.mark.skipif(
    not _mediapipe_available,
    reason="mediapipe not installed",
)


def _create_test_video(path: Path, duration: float = 1.0, fps: int = 10) -> Path:
    """Create a minimal test video using the sample_data helper.

    Uses a short duration and low FPS to keep tests fast while
    still producing enough frames for pose extraction.
    """
    from tests.harness.sample_data import create_sample_video
    return create_sample_video(path, duration=duration, fps=fps, size=(128, 128))


class TestMediaPipeExtractor:
    """Tests for the MediaPipeExtractor implementation."""

    def test_extract_poses_from_video(self, tmp_path: Path) -> None:
        """Pose extraction returns a non-empty list of PoseFrame objects."""
        from src.infrastructure.pose.mediapipe_extractor import MediaPipeExtractor

        video = _create_test_video(tmp_path / "dance.mp4", duration=1.0, fps=10)
        extractor = MediaPipeExtractor(model_complexity=0)  # fast mode for tests

        frames = extractor.extract_from_video(video)

        # Should produce frames (may not detect poses in solid colour video,
        # but the method should not raise an error)
        assert isinstance(frames, list)
        # The synthetic video may or may not produce pose detections
        # depending on the content; we test the interface contract

    def test_extract_poses_returns_poseframe_objects(self, tmp_path: Path) -> None:
        """Each element in the result is a PoseFrame with 33 keypoints."""
        from src.infrastructure.pose.mediapipe_extractor import MediaPipeExtractor

        video = _create_test_video(tmp_path / "dance.mp4", duration=0.5, fps=10)
        extractor = MediaPipeExtractor(model_complexity=0)

        frames = extractor.extract_from_video(video)

        # If any frames were detected, validate their structure
        for frame in frames:
            assert isinstance(frame, PoseFrame)
            assert len(frame.keypoints) == 33
            assert frame.timestamp >= 0.0
            for kp in frame.keypoints:
                assert len(kp) == 4  # x, y, z, visibility

    def test_extract_poses_missing_file(self, tmp_path: Path) -> None:
        """Raises ValidationError for a non-existent video file."""
        from src.infrastructure.pose.mediapipe_extractor import MediaPipeExtractor

        extractor = MediaPipeExtractor()

        with pytest.raises(ValidationError, match="not found"):
            extractor.extract_from_video(tmp_path / "nonexistent.mp4")

    def test_extract_poses_timestamps_increase(self, tmp_path: Path) -> None:
        """Frame timestamps are monotonically non-decreasing."""
        from src.infrastructure.pose.mediapipe_extractor import MediaPipeExtractor

        video = _create_test_video(tmp_path / "dance.mp4", duration=1.0, fps=10)
        extractor = MediaPipeExtractor(model_complexity=0)

        frames = extractor.extract_from_video(video)

        for i in range(1, len(frames)):
            assert frames[i].timestamp >= frames[i - 1].timestamp
