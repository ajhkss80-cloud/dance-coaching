"""Unit tests for domain entities."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.entities import CoachJob, GenerateJob, Segment


class TestSegment:
    """Tests for the Segment entity."""

    def test_segment_duration_calculation(self) -> None:
        """Segment duration is correctly computed from start and end times."""
        segment = Segment(index=0, start_time=1.5, end_time=4.5)
        assert segment.duration == pytest.approx(3.0)

    def test_segment_duration_small_values(self) -> None:
        """Duration is correct for very small segments."""
        segment = Segment(index=0, start_time=0.0, end_time=0.033)
        assert segment.duration == pytest.approx(0.033)

    def test_segment_frozen(self) -> None:
        """Segment is immutable (frozen dataclass)."""
        segment = Segment(index=0, start_time=0.0, end_time=5.0)
        with pytest.raises(AttributeError):
            segment.start_time = 1.0  # type: ignore[misc]

    def test_segment_rejects_negative_start(self) -> None:
        """Segment rejects negative start_time."""
        with pytest.raises(ValueError, match="non-negative"):
            Segment(index=0, start_time=-1.0, end_time=5.0)

    def test_segment_rejects_end_before_start(self) -> None:
        """Segment rejects end_time <= start_time."""
        with pytest.raises(ValueError, match="greater than"):
            Segment(index=0, start_time=5.0, end_time=3.0)

    def test_segment_rejects_equal_times(self) -> None:
        """Segment rejects end_time equal to start_time."""
        with pytest.raises(ValueError, match="greater than"):
            Segment(index=0, start_time=5.0, end_time=5.0)

    def test_segment_rejects_negative_index(self) -> None:
        """Segment rejects negative index."""
        with pytest.raises(ValueError, match="non-negative"):
            Segment(index=-1, start_time=0.0, end_time=5.0)


class TestGenerateJob:
    """Tests for the GenerateJob entity."""

    @pytest.fixture()
    def job(self) -> GenerateJob:
        """Create a standard test job."""
        return GenerateJob(
            job_id="test-001",
            avatar_path=Path("/tmp/avatar.png"),
            reference_path=Path("/tmp/reference.mp4"),
            backend_type="cloud",
        )

    def test_default_state(self, job: GenerateJob) -> None:
        """New job starts with pending status and zero progress."""
        assert job.status == "pending"
        assert job.progress == 0.0
        assert job.segments == []
        assert job.error_message is None

    def test_progress_update(self, job: GenerateJob) -> None:
        """Progress can be updated to valid values."""
        job.update_progress(50.0)
        assert job.progress == 50.0

    def test_progress_update_transitions_to_processing(self, job: GenerateJob) -> None:
        """Updating progress on a pending job transitions it to processing."""
        assert job.status == "pending"
        job.update_progress(10.0)
        assert job.status == "processing"

    def test_progress_update_rejects_negative(self, job: GenerateJob) -> None:
        """Progress update rejects negative values."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            job.update_progress(-1.0)

    def test_progress_update_rejects_over_100(self, job: GenerateJob) -> None:
        """Progress update rejects values above 100."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            job.update_progress(101.0)

    def test_progress_validation_on_construction(self) -> None:
        """Invalid progress on construction raises ValueError."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            GenerateJob(
                job_id="bad",
                avatar_path=Path("/tmp/a.png"),
                reference_path=Path("/tmp/r.mp4"),
                backend_type="cloud",
                progress=150.0,
            )

    def test_complete(self, job: GenerateJob) -> None:
        """Completing a job sets progress to 100 and status to completed."""
        job.complete()
        assert job.status == "completed"
        assert job.progress == 100.0

    def test_fail(self, job: GenerateJob) -> None:
        """Failing a job sets status and records the error message."""
        job.fail("GPU OOM")
        assert job.status == "failed"
        assert job.error_message == "GPU OOM"

    def test_status_transitions(self, job: GenerateJob) -> None:
        """Job transitions through the expected lifecycle."""
        assert job.status == "pending"
        job.update_progress(25.0)
        assert job.status == "processing"
        job.complete()
        assert job.status == "completed"

    def test_invalid_status_on_construction(self) -> None:
        """Invalid status on construction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            GenerateJob(
                job_id="bad",
                avatar_path=Path("/tmp/a.png"),
                reference_path=Path("/tmp/r.mp4"),
                backend_type="cloud",
                status="unknown",
            )


class TestCoachJob:
    """Tests for the CoachJob entity."""

    def test_creation(self) -> None:
        """CoachJob can be created with required fields."""
        job = CoachJob(
            job_id="coach-001",
            user_video_path=Path("/tmp/user.mp4"),
            reference_video_path=Path("/tmp/ref.mp4"),
        )
        assert job.job_id == "coach-001"
        assert job.status == "pending"
        assert job.progress == 0.0

    def test_progress_update(self) -> None:
        """CoachJob progress updates correctly."""
        job = CoachJob(
            job_id="coach-002",
            user_video_path=Path("/tmp/user.mp4"),
            reference_video_path=Path("/tmp/ref.mp4"),
        )
        job.update_progress(50.0)
        assert job.progress == 50.0
        assert job.status == "processing"

    def test_complete(self) -> None:
        """CoachJob completes correctly."""
        job = CoachJob(
            job_id="coach-003",
            user_video_path=Path("/tmp/user.mp4"),
            reference_video_path=Path("/tmp/ref.mp4"),
        )
        job.complete()
        assert job.status == "completed"
        assert job.progress == 100.0

    def test_fail(self) -> None:
        """CoachJob fails correctly with error message."""
        job = CoachJob(
            job_id="coach-004",
            user_video_path=Path("/tmp/user.mp4"),
            reference_video_path=Path("/tmp/ref.mp4"),
        )
        job.fail("No poses detected")
        assert job.status == "failed"
        assert job.error_message == "No poses detected"
