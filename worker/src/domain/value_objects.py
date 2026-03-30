"""Domain value objects for the Dance Coaching Platform.

Immutable value types that encapsulate domain concepts.
Domain layer uses only stdlib -- numpy is imported lazily
via a method that infrastructure code calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BackendType(Enum):
    """Supported video generation backend types."""

    CLOUD = "cloud"
    LOCAL = "local"

    @classmethod
    def from_string(cls, value: str) -> BackendType:
        """Create a BackendType from a string value.

        Args:
            value: String representation of the backend type.

        Returns:
            The corresponding BackendType enum member.

        Raises:
            ValueError: If the value does not match any backend type.
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        valid = ", ".join(m.value for m in cls)
        raise ValueError(
            f"Invalid backend type '{value}'. Must be one of: {valid}"
        )


@dataclass(frozen=True)
class PoseFrame:
    """A single frame of pose estimation data.

    Contains 33 MediaPipe Pose landmarks, each with (x, y, z, visibility).
    Coordinates are normalized to [0, 1] relative to the image dimensions.
    """

    timestamp: float  # seconds
    keypoints: list[tuple[float, float, float, float]]  # 33 joints: x, y, z, visibility

    _EXPECTED_JOINTS = 33

    def __post_init__(self) -> None:
        if len(self.keypoints) != self._EXPECTED_JOINTS:
            raise ValueError(
                f"Expected {self._EXPECTED_JOINTS} keypoints, "
                f"got {len(self.keypoints)}"
            )
        if self.timestamp < 0:
            raise ValueError(
                f"Timestamp must be non-negative, got {self.timestamp}"
            )

    def to_flat_vector(self) -> "numpy.ndarray":
        """Flatten keypoints to a 99-dimensional vector (33 joints * 3 coords).

        Excludes the visibility component, keeping only x, y, z per joint.
        This method imports numpy at call time to keep the domain layer
        free of heavy dependencies at import time.

        Returns:
            A numpy array of shape (99,) with dtype float64.
        """
        import numpy as np

        coords = []
        for x, y, z, _visibility in self.keypoints:
            coords.extend([x, y, z])
        return np.array(coords, dtype=np.float64)


@dataclass(frozen=True)
class Score:
    """A score value constrained to [0, 100]."""

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(
                f"Score must be between 0 and 100, got {self.value}"
            )

    def to_percentage(self) -> str:
        """Format the score as a percentage string.

        Returns:
            A string like '85.0%'.
        """
        return f"{self.value:.1f}%"


@dataclass(frozen=True)
class JointScores:
    """Per-joint-group scoring for dance coaching feedback.

    Each joint group receives an independent Score. The overall score
    is a weighted average reflecting the relative importance of each
    body region to dance performance.
    """

    left_arm: Score
    right_arm: Score
    left_leg: Score
    right_leg: Score
    torso: Score
    head: Score

    # Weights reflect dance performance importance
    _WEIGHTS: dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # Cannot set class-level dict on frozen dataclass, so we use a method
        pass

    @staticmethod
    def _get_weights() -> dict[str, float]:
        """Return scoring weights for each joint group."""
        return {
            "left_arm": 0.15,
            "right_arm": 0.15,
            "left_leg": 0.20,
            "right_leg": 0.20,
            "torso": 0.20,
            "head": 0.10,
        }

    def overall(self) -> Score:
        """Calculate the weighted average score across all joint groups.

        Returns:
            A Score representing the overall performance.
        """
        weights = self._get_weights()
        weighted_sum = (
            self.left_arm.value * weights["left_arm"]
            + self.right_arm.value * weights["right_arm"]
            + self.left_leg.value * weights["left_leg"]
            + self.right_leg.value * weights["right_leg"]
            + self.torso.value * weights["torso"]
            + self.head.value * weights["head"]
        )
        return Score(value=round(weighted_sum, 2))
