"""Unit tests for the CoachDanceUseCase with real DTW and scorer."""
from __future__ import annotations

import asyncio
from math import sin
from pathlib import Path

import pytest

from src.application.use_cases.coach_dance import CoachDanceUseCase
from src.infrastructure.coaching.dtw_aligner import DTWAligner
from src.infrastructure.coaching.scorer import DanceScorer
from tests.harness.fake_pose_extractor import FakePoseExtractor


@pytest.fixture
def tmp_videos(tmp_path: Path) -> tuple[Path, Path]:
    """Create two dummy video files for path validation."""
    user_video = tmp_path / "user.mp4"
    ref_video = tmp_path / "reference.mp4"
    user_video.write_bytes(b"fake-user-video")
    ref_video.write_bytes(b"fake-ref-video")
    return user_video, ref_video


@pytest.fixture
def coach_use_case() -> CoachDanceUseCase:
    """Build a CoachDanceUseCase with fake extractor + real DTW + real scorer."""
    return CoachDanceUseCase(
        pose_extractor=FakePoseExtractor(num_frames=30, fps=30),
        aligner=DTWAligner(),
        scorer=DanceScorer(),
    )


class TestCoachingFullFlow:
    """End-to-end coaching pipeline with fake extractor and real analysis."""

    @pytest.mark.asyncio
    async def test_coaching_full_flow(
        self,
        coach_use_case: CoachDanceUseCase,
        tmp_videos: tuple[Path, Path],
    ) -> None:
        user_video, ref_video = tmp_videos
        progress_values: list[float] = []

        result = await coach_use_case.execute(
            job_id="test-job-1",
            user_video=str(user_video),
            reference_video=str(ref_video),
            progress_callback=progress_values.append,
        )

        assert result["status"] == "completed"
        assert result["job_id"] == "test-job-1"
        assert "overall_score" in result
        assert "joint_scores" in result
        assert "feedback" in result
        assert "worst_segments" in result

        # Progress should have been reported
        assert len(progress_values) >= 4
        assert progress_values[-1] == 100.0

    @pytest.mark.asyncio
    async def test_coaching_result_format(
        self,
        coach_use_case: CoachDanceUseCase,
        tmp_videos: tuple[Path, Path],
    ) -> None:
        """Verify all expected fields are present and correctly typed."""
        user_video, ref_video = tmp_videos

        result = await coach_use_case.execute(
            job_id="format-test",
            user_video=str(user_video),
            reference_video=str(ref_video),
        )

        # Overall score is a float in [0, 100]
        assert isinstance(result["overall_score"], float)
        assert 0.0 <= result["overall_score"] <= 100.0

        # Joint scores dict has all 6 groups
        js = result["joint_scores"]
        expected_groups = {"left_arm", "right_arm", "left_leg", "right_leg", "torso", "head"}
        assert set(js.keys()) == expected_groups
        for group_name, score_val in js.items():
            assert isinstance(score_val, float)
            assert 0.0 <= score_val <= 100.0

        # Feedback is a non-empty list of strings
        assert isinstance(result["feedback"], list)
        assert len(result["feedback"]) > 0
        for fb in result["feedback"]:
            assert isinstance(fb, str)

        # Worst segments is a list of dicts
        assert isinstance(result["worst_segments"], list)


class TestCoachingIdenticalVideos:
    """When both videos produce identical poses, score should be ~100."""

    @pytest.mark.asyncio
    async def test_coaching_identical_videos(
        self,
        tmp_videos: tuple[Path, Path],
    ) -> None:
        # Both videos go through the same FakePoseExtractor, so poses are
        # identical (same num_frames, same deterministic sine patterns)
        use_case = CoachDanceUseCase(
            pose_extractor=FakePoseExtractor(num_frames=30, fps=30),
            aligner=DTWAligner(),
            scorer=DanceScorer(),
        )
        user_video, ref_video = tmp_videos

        result = await use_case.execute(
            job_id="identical-test",
            user_video=str(user_video),
            reference_video=str(ref_video),
        )

        assert result["status"] == "completed"
        # Identical poses should produce a perfect score
        assert result["overall_score"] == 100.0


class TestCoachingErrorHandling:
    """Error handling in the coaching pipeline."""

    @pytest.mark.asyncio
    async def test_coaching_missing_user_video(self) -> None:
        use_case = CoachDanceUseCase(
            pose_extractor=FakePoseExtractor(),
            aligner=DTWAligner(),
            scorer=DanceScorer(),
        )

        result = await use_case.execute(
            job_id="missing-user",
            user_video="/nonexistent/user.mp4",
            reference_video="/nonexistent/ref.mp4",
        )

        assert result["status"] == "failed"
        assert "error" in result
        assert "User video not found" in result["error"]

    @pytest.mark.asyncio
    async def test_coaching_missing_reference_video(
        self,
        tmp_path: Path,
    ) -> None:
        user_video = tmp_path / "user.mp4"
        user_video.write_bytes(b"fake")

        use_case = CoachDanceUseCase(
            pose_extractor=FakePoseExtractor(),
            aligner=DTWAligner(),
            scorer=DanceScorer(),
        )

        result = await use_case.execute(
            job_id="missing-ref",
            user_video=str(user_video),
            reference_video="/nonexistent/ref.mp4",
        )

        assert result["status"] == "failed"
        assert "Reference video not found" in result["error"]

    @pytest.mark.asyncio
    async def test_coaching_no_progress_callback(
        self,
        tmp_videos: tuple[Path, Path],
    ) -> None:
        """Pipeline works without a progress callback."""
        use_case = CoachDanceUseCase(
            pose_extractor=FakePoseExtractor(num_frames=20, fps=30),
            aligner=DTWAligner(),
            scorer=DanceScorer(),
        )
        user_video, ref_video = tmp_videos

        result = await use_case.execute(
            job_id="no-callback",
            user_video=str(user_video),
            reference_video=str(ref_video),
        )

        assert result["status"] == "completed"
