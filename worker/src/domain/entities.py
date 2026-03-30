"""Domain entities for the Dance Coaching Platform.

Pure domain objects using only stdlib dataclasses. No external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    """Represents a time-bounded segment of a video for processing."""

    index: int
    start_time: float  # seconds
    end_time: float  # seconds

    def __post_init__(self) -> None:
        if self.start_time < 0:
            raise ValueError(f"start_time must be non-negative, got {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be greater than "
                f"start_time ({self.start_time})"
            )
        if self.index < 0:
            raise ValueError(f"index must be non-negative, got {self.index}")

    @property
    def duration(self) -> float:
        """Duration of the segment in seconds."""
        return self.end_time - self.start_time


@dataclass
class GenerateJob:
    """Represents a video generation job for creating dance tutorials.

    Tracks the lifecycle of generating an avatar-driven dance video
    from a reference choreography.
    """

    job_id: str
    avatar_path: Path
    reference_path: Path
    backend_type: str  # stored as string, validated via BackendType value object
    segments: list[Segment] = field(default_factory=list)
    progress: float = 0.0
    status: str = "pending"  # pending, processing, completed, failed
    error_message: str | None = None

    _VALID_STATUSES = {"pending", "processing", "completed", "failed"}

    def __post_init__(self) -> None:
        if self.status not in self._VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of {self._VALID_STATUSES}"
            )
        if not (0.0 <= self.progress <= 100.0):
            raise ValueError(
                f"Progress must be between 0 and 100, got {self.progress}"
            )

    def update_progress(self, value: float) -> None:
        """Update the job progress percentage.

        Args:
            value: Progress value between 0 and 100.

        Raises:
            ValueError: If value is outside the valid range.
        """
        if not (0.0 <= value <= 100.0):
            raise ValueError(
                f"Progress must be between 0 and 100, got {value}"
            )
        self.progress = value
        if self.status == "pending":
            self.status = "processing"

    def complete(self) -> None:
        """Mark the job as completed."""
        self.progress = 100.0
        self.status = "completed"

    def fail(self, error_msg: str) -> None:
        """Mark the job as failed with an error message.

        Args:
            error_msg: Description of the failure.
        """
        self.status = "failed"
        self.error_message = error_msg


@dataclass
class CoachJob:
    """Represents a coaching analysis job comparing user dance to reference.

    Tracks the lifecycle of analyzing a user's dance performance
    against a reference choreography.
    """

    job_id: str
    user_video_path: Path
    reference_video_path: Path
    progress: float = 0.0
    status: str = "pending"  # pending, processing, completed, failed
    error_message: str | None = None

    _VALID_STATUSES = {"pending", "processing", "completed", "failed"}

    def __post_init__(self) -> None:
        if self.status not in self._VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of {self._VALID_STATUSES}"
            )
        if not (0.0 <= self.progress <= 100.0):
            raise ValueError(
                f"Progress must be between 0 and 100, got {self.progress}"
            )

    def update_progress(self, value: float) -> None:
        """Update the job progress percentage."""
        if not (0.0 <= value <= 100.0):
            raise ValueError(
                f"Progress must be between 0 and 100, got {value}"
            )
        self.progress = value
        if self.status == "pending":
            self.status = "processing"

    def complete(self) -> None:
        """Mark the job as completed."""
        self.progress = 100.0
        self.status = "completed"

    def fail(self, error_msg: str) -> None:
        """Mark the job as failed."""
        self.status = "failed"
        self.error_message = error_msg
