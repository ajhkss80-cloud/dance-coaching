"""Ports (interfaces) for dance coaching analysis components.

Defines the contracts for temporal alignment and scoring of dance
performances, allowing infrastructure implementations to be swapped
without affecting the application layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.domain.value_objects import JointScores, PoseFrame, Score


@dataclass(frozen=True)
class DTWResult:
    """Result of Dynamic Time Warping alignment between two pose sequences.

    Attributes:
        aligned_pairs: List of (reference_index, user_index) tuples
            representing the optimal alignment path.
        total_distance: Sum of distances along the alignment path.
        normalized_distance: Total distance divided by the number of
            aligned pairs, providing a length-independent metric.
    """

    aligned_pairs: list[tuple[int, int]]
    total_distance: float
    normalized_distance: float


@dataclass(frozen=True)
class ScoringResult:
    """Complete scoring output from dance performance analysis.

    Attributes:
        overall_score: Weighted average score across all joint groups.
        joint_scores: Per-joint-group scoring breakdown.
        feedback: Ordered list of human-readable coaching feedback strings.
        worst_segments: Time segments with lowest scores, each containing
            start_time, end_time, body_part, and score.
    """

    overall_score: Score
    joint_scores: JointScores
    feedback: list[str]
    worst_segments: list[dict]


class DanceAligner(ABC):
    """Abstract base class for temporal alignment of pose sequences.

    Implementations align a user's dance performance to a reference
    choreography, finding the optimal frame-to-frame correspondence.
    """

    @abstractmethod
    def align(
        self,
        reference: list[PoseFrame],
        user: list[PoseFrame],
    ) -> DTWResult:
        """Align user poses to reference poses using temporal warping.

        Args:
            reference: Reference choreography pose sequence.
            user: User's dance performance pose sequence.

        Returns:
            A DTWResult containing the optimal alignment path and
            distance metrics.
        """
        ...


class DanceScorerPort(ABC):
    """Abstract base class for scoring aligned dance performances.

    Implementations compute per-joint-group accuracy scores and
    generate actionable coaching feedback.
    """

    @abstractmethod
    def score(
        self,
        aligned_pairs: list[tuple[int, int]],
        ref_poses: list[PoseFrame],
        user_poses: list[PoseFrame],
    ) -> ScoringResult:
        """Score the user's performance against aligned reference poses.

        Args:
            aligned_pairs: List of (reference_index, user_index) tuples
                from the alignment step.
            ref_poses: Full reference pose sequence.
            user_poses: Full user pose sequence.

        Returns:
            A ScoringResult with per-joint scores, overall score,
            feedback strings, and worst performing segments.
        """
        ...
