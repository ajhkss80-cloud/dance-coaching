"""Dance performance scoring based on aligned pose comparison.

Computes per-joint-group accuracy scores by comparing aligned pose
pairs between a reference choreography and a user's performance.
Generates actionable feedback and identifies worst-performing segments.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from src.application.ports.coaching import DanceScorerPort, ScoringResult
from src.domain.value_objects import JointScores, PoseFrame, Score

logger = logging.getLogger(__name__)

# MediaPipe joint indices grouped by body region
JOINT_GROUPS: dict[str, list[int]] = {
    "left_arm": [11, 13, 15],      # shoulder, elbow, wrist
    "right_arm": [12, 14, 16],
    "left_leg": [23, 25, 27],      # hip, knee, ankle
    "right_leg": [24, 26, 28],
    "torso": [11, 12, 23, 24],     # shoulders + hips
    "head": [0, 7, 8],             # nose + ears
}

JOINT_WEIGHTS: dict[str, float] = {
    "left_arm": 0.15,
    "right_arm": 0.15,
    "left_leg": 0.20,
    "right_leg": 0.20,
    "torso": 0.20,
    "head": 0.10,
}

# Distance thresholds for score mapping
_PERFECT_DISTANCE = 0.0
_ZERO_SCORE_DISTANCE = 0.3

# Segment analysis window size (number of aligned pairs per segment)
_SEGMENT_WINDOW = 15


def _distance_to_score(distance: float) -> float:
    """Map a per-joint Euclidean distance to a 0-100 score.

    Uses linear interpolation: distance 0.0 maps to score 100,
    distance >= 0.3 maps to score 0.

    Args:
        distance: Average Euclidean distance for a joint group.

    Returns:
        A float score in [0, 100].
    """
    if distance <= _PERFECT_DISTANCE:
        return 100.0
    if distance >= _ZERO_SCORE_DISTANCE:
        return 0.0
    return 100.0 * (1.0 - distance / _ZERO_SCORE_DISTANCE)


def _compute_joint_group_distance(
    ref_keypoints: list[tuple[float, float, float, float]],
    user_keypoints: list[tuple[float, float, float, float]],
    joint_indices: list[int],
) -> float:
    """Compute average Euclidean distance for a joint group.

    Compares (x, y, z) coordinates between reference and user for
    each joint in the group, excluding visibility.

    Args:
        ref_keypoints: Reference frame's 33 keypoints.
        user_keypoints: User frame's 33 keypoints.
        joint_indices: Indices of joints in this group.

    Returns:
        Average Euclidean distance across the joints in the group.
    """
    total_dist = 0.0
    for idx in joint_indices:
        rx, ry, rz, _ = ref_keypoints[idx]
        ux, uy, uz, _ = user_keypoints[idx]
        dist = np.sqrt((rx - ux) ** 2 + (ry - uy) ** 2 + (rz - uz) ** 2)
        total_dist += dist
    return total_dist / len(joint_indices)


def _generate_feedback_for_group(group_name: str, score_value: float) -> str | None:
    """Generate a feedback string for a joint group based on its score.

    Args:
        group_name: Human-readable body part name.
        score_value: Score in [0, 100].

    Returns:
        A feedback string, or None if score is above the feedback threshold.
    """
    readable_name = group_name.replace("_", " ")

    if score_value < 30:
        return (
            f"Your {readable_name} needs significant work. "
            f"Focus on matching the reference movement."
        )
    if score_value < 50:
        return (
            f"Your {readable_name} is getting there but needs more practice."
        )
    if score_value < 70:
        return (
            f"Your {readable_name} looks decent. Keep refining the details."
        )
    if score_value < 85:
        return (
            f"Your {readable_name} is looking good! Minor adjustments needed."
        )
    return f"Excellent {readable_name} movement! Very close to the reference."


class DanceScorer(DanceScorerPort):
    """Scores dance performances by comparing aligned pose pairs.

    For each aligned frame pair, computes per-joint-group Euclidean
    distance and maps it to a 0-100 score. Produces weighted overall
    scores, coaching feedback, and identifies worst-performing time
    segments.
    """

    def score(
        self,
        aligned_pairs: list[tuple[int, int]],
        ref_poses: list[PoseFrame],
        user_poses: list[PoseFrame],
    ) -> ScoringResult:
        """Score aligned dance performance.

        Args:
            aligned_pairs: List of (ref_index, user_index) tuples.
            ref_poses: Full reference pose sequence.
            user_poses: Full user pose sequence.

        Returns:
            ScoringResult with scores, feedback, and worst segments.
        """
        if not aligned_pairs:
            zero_score = Score(value=0.0)
            return ScoringResult(
                overall_score=zero_score,
                joint_scores=JointScores(
                    left_arm=zero_score,
                    right_arm=zero_score,
                    left_leg=zero_score,
                    right_leg=zero_score,
                    torso=zero_score,
                    head=zero_score,
                ),
                feedback=["No aligned frames to score."],
                worst_segments=[],
            )

        # Accumulate per-group distances across all aligned pairs
        group_distances: dict[str, list[float]] = {
            name: [] for name in JOINT_GROUPS
        }

        for ref_idx, user_idx in aligned_pairs:
            ref_kp = ref_poses[ref_idx].keypoints
            user_kp = user_poses[user_idx].keypoints

            for group_name, joint_indices in JOINT_GROUPS.items():
                dist = _compute_joint_group_distance(ref_kp, user_kp, joint_indices)
                group_distances[group_name].append(dist)

        # Compute average distance per group and map to scores
        group_scores: dict[str, float] = {}
        for group_name, distances in group_distances.items():
            avg_dist = float(np.mean(distances))
            group_scores[group_name] = _distance_to_score(avg_dist)

        joint_scores = JointScores(
            left_arm=Score(value=round(group_scores["left_arm"], 2)),
            right_arm=Score(value=round(group_scores["right_arm"], 2)),
            left_leg=Score(value=round(group_scores["left_leg"], 2)),
            right_leg=Score(value=round(group_scores["right_leg"], 2)),
            torso=Score(value=round(group_scores["torso"], 2)),
            head=Score(value=round(group_scores["head"], 2)),
        )

        overall_score = joint_scores.overall()

        # Generate feedback for each joint group, sorted by score ascending
        feedback: list[str] = []
        sorted_groups = sorted(group_scores.items(), key=lambda x: x[1])
        for group_name, score_val in sorted_groups:
            fb = _generate_feedback_for_group(group_name, score_val)
            if fb is not None:
                feedback.append(fb)

        # Identify worst segments using a sliding window
        worst_segments = self._find_worst_segments(
            aligned_pairs, ref_poses, user_poses, group_distances
        )

        logger.info(
            "Scoring complete: overall=%.1f, groups=%s",
            overall_score.value,
            {k: f"{v:.1f}" for k, v in group_scores.items()},
        )

        return ScoringResult(
            overall_score=overall_score,
            joint_scores=joint_scores,
            feedback=feedback,
            worst_segments=worst_segments,
        )

    def _find_worst_segments(
        self,
        aligned_pairs: list[tuple[int, int]],
        ref_poses: list[PoseFrame],
        user_poses: list[PoseFrame],
        group_distances: dict[str, list[float]],
    ) -> list[dict]:
        """Identify time segments with the worst performance.

        Slides a window across aligned pairs, computing average scores
        per group within each window. Returns segments where any group
        falls below a threshold.

        Args:
            aligned_pairs: Alignment path indices.
            ref_poses: Reference pose sequence.
            user_poses: User pose sequence.
            group_distances: Per-pair distances for each joint group.

        Returns:
            List of dicts with start_time, end_time, body_part, score.
        """
        num_pairs = len(aligned_pairs)
        if num_pairs < _SEGMENT_WINDOW:
            # Not enough data for segment analysis; treat whole as one segment
            window_size = num_pairs
        else:
            window_size = _SEGMENT_WINDOW

        worst_segments: list[dict] = []
        worst_threshold = 50.0  # Only report segments below this score

        step = max(1, window_size // 2)  # 50% overlap between windows

        for start in range(0, num_pairs - window_size + 1, step):
            end = start + window_size

            for group_name, distances in group_distances.items():
                window_distances = distances[start:end]
                avg_dist = float(np.mean(window_distances))
                segment_score = _distance_to_score(avg_dist)

                if segment_score < worst_threshold:
                    ref_start_idx = aligned_pairs[start][0]
                    ref_end_idx = aligned_pairs[end - 1][0]
                    start_time = ref_poses[ref_start_idx].timestamp
                    end_time = ref_poses[ref_end_idx].timestamp

                    worst_segments.append({
                        "start_time": round(start_time, 3),
                        "end_time": round(end_time, 3),
                        "body_part": group_name,
                        "score": round(segment_score, 2),
                    })

        # Sort by score ascending (worst first) and limit results
        worst_segments.sort(key=lambda s: s["score"])
        return worst_segments[:10]
