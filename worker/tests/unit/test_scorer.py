"""Unit tests for the dance scorer."""
from __future__ import annotations

import random
from math import sin

import pytest

from src.domain.value_objects import JointScores, PoseFrame, Score
from src.infrastructure.coaching.scorer import (
    DanceScorer,
    JOINT_GROUPS,
    JOINT_WEIGHTS,
    _distance_to_score,
    _generate_feedback_for_group,
)


def _make_pose_frame(
    timestamp: float,
    offset: float = 0.0,
    randomize: bool = False,
    rng: random.Random | None = None,
) -> PoseFrame:
    """Create a PoseFrame with sine-wave or randomized keypoints."""
    keypoints = []
    for j in range(33):
        if randomize and rng is not None:
            x = rng.random()
            y = rng.random()
            z = rng.random() * 0.5
        else:
            x = 0.5 + 0.1 * sin(timestamp * 2.0 + j * 0.1 + offset)
            y = 0.5 + 0.05 * j / 33.0 + 0.02 * sin(timestamp + offset)
            z = 0.0
        keypoints.append((x, y, z, 0.99))
    return PoseFrame(timestamp=timestamp, keypoints=keypoints)


def _make_sequence(
    num_frames: int,
    fps: float = 30.0,
    offset: float = 0.0,
    randomize: bool = False,
    seed: int = 42,
) -> list[PoseFrame]:
    """Generate a sequence of PoseFrames."""
    rng = random.Random(seed) if randomize else None
    return [
        _make_pose_frame(i / fps, offset=offset, randomize=randomize, rng=rng)
        for i in range(num_frames)
    ]


def _identity_pairs(n: int) -> list[tuple[int, int]]:
    """Create diagonal alignment pairs (i, i) for n frames."""
    return [(i, i) for i in range(n)]


class TestScoreIdenticalPoses:
    """Identical poses should score 100."""

    def test_score_identical_poses_is_100(self) -> None:
        scorer = DanceScorer()
        seq = _make_sequence(30)
        pairs = _identity_pairs(30)

        result = scorer.score(pairs, seq, seq)

        assert result.overall_score.value == 100.0
        assert result.joint_scores.left_arm.value == 100.0
        assert result.joint_scores.right_arm.value == 100.0
        assert result.joint_scores.left_leg.value == 100.0
        assert result.joint_scores.right_leg.value == 100.0
        assert result.joint_scores.torso.value == 100.0
        assert result.joint_scores.head.value == 100.0


class TestScoreVeryDifferentPoses:
    """Very different poses should score low."""

    def test_score_very_different_poses_is_low(self) -> None:
        scorer = DanceScorer()
        ref = _make_sequence(30, offset=0.0)
        user = _make_sequence(30, randomize=True, seed=99)
        pairs = _identity_pairs(30)

        result = scorer.score(pairs, ref, user)

        # Random poses should produce a low score
        assert result.overall_score.value < 60.0


class TestJointScoresIndependent:
    """Bad arms with good legs should produce different per-group scores."""

    def test_joint_scores_independent(self) -> None:
        scorer = DanceScorer()
        num = 30

        # Create ref and user sequences where arms differ but legs match
        ref = _make_sequence(num)
        user_frames = []
        for i, ref_frame in enumerate(ref):
            kp = list(ref_frame.keypoints)
            # Corrupt arm joints (11, 12, 13, 14, 15, 16) by shifting x
            for arm_idx in [11, 12, 13, 14, 15, 16]:
                x, y, z, v = kp[arm_idx]
                kp[arm_idx] = (x + 0.4, y + 0.4, z, v)  # large shift
            user_frames.append(PoseFrame(timestamp=ref_frame.timestamp, keypoints=kp))

        pairs = _identity_pairs(num)
        result = scorer.score(pairs, ref, user_frames)

        # Arms should score much lower than legs
        assert result.joint_scores.left_arm.value < 30.0
        assert result.joint_scores.right_arm.value < 30.0
        # Legs should still be perfect (100)
        assert result.joint_scores.left_leg.value == 100.0
        assert result.joint_scores.right_leg.value == 100.0


class TestFeedbackGeneration:
    """Feedback strings follow the scoring thresholds."""

    def test_feedback_generation_bad_score(self) -> None:
        fb = _generate_feedback_for_group("left_arm", 20.0)
        assert fb is not None
        assert "needs significant work" in fb
        assert "left arm" in fb

    def test_feedback_generation_mediocre_score(self) -> None:
        fb = _generate_feedback_for_group("right_leg", 45.0)
        assert fb is not None
        assert "getting there" in fb

    def test_feedback_generation_decent_score(self) -> None:
        fb = _generate_feedback_for_group("torso", 60.0)
        assert fb is not None
        assert "looks decent" in fb

    def test_feedback_generation_good_score(self) -> None:
        fb = _generate_feedback_for_group("head", 80.0)
        assert fb is not None
        assert "looking good" in fb

    def test_feedback_generation_excellent_score(self) -> None:
        fb = _generate_feedback_for_group("left_leg", 90.0)
        assert fb is not None
        assert "Excellent" in fb

    def test_feedback_boundary_30(self) -> None:
        """Score exactly 30 should be 'getting there', not 'significant work'."""
        fb = _generate_feedback_for_group("torso", 30.0)
        assert "getting there" in fb

    def test_feedback_boundary_85(self) -> None:
        """Score exactly 85 should be 'Excellent'."""
        fb = _generate_feedback_for_group("head", 85.0)
        assert "Excellent" in fb


class TestWorstSegmentsIdentified:
    """Worst segments are detected from aligned pair distances."""

    def test_worst_segments_identified(self) -> None:
        scorer = DanceScorer()
        num = 60

        # Create a sequence where the first 30 frames are bad, last 30 are good
        ref = _make_sequence(num)
        user_frames = []
        for i, ref_frame in enumerate(ref):
            kp = list(ref_frame.keypoints)
            if i < 30:
                # Corrupt all joints for first half
                for j in range(33):
                    x, y, z, v = kp[j]
                    kp[j] = (x + 0.5, y + 0.5, z, v)
            user_frames.append(PoseFrame(timestamp=ref_frame.timestamp, keypoints=kp))

        pairs = _identity_pairs(num)
        result = scorer.score(pairs, ref, user_frames)

        # Should have identified worst segments in the first half
        assert len(result.worst_segments) > 0
        # Worst segments should be in the early time range
        for seg in result.worst_segments:
            assert "start_time" in seg
            assert "end_time" in seg
            assert "body_part" in seg
            assert "score" in seg
            assert seg["score"] < 50.0

    def test_no_worst_segments_for_perfect_match(self) -> None:
        scorer = DanceScorer()
        seq = _make_sequence(30)
        pairs = _identity_pairs(30)

        result = scorer.score(pairs, seq, seq)

        assert result.worst_segments == []


class TestOverallIsWeightedAverage:
    """Overall score must equal the weighted average of joint group scores."""

    def test_overall_is_weighted_average(self) -> None:
        scorer = DanceScorer()
        num = 30

        # Create user with varying offsets per joint group to get different scores
        ref = _make_sequence(num)
        user_frames = []
        for i, ref_frame in enumerate(ref):
            kp = list(ref_frame.keypoints)
            # Shift torso joints slightly
            for idx in JOINT_GROUPS["torso"]:
                x, y, z, v = kp[idx]
                kp[idx] = (x + 0.1, y + 0.1, z, v)
            # Shift head joints more
            for idx in JOINT_GROUPS["head"]:
                x, y, z, v = kp[idx]
                kp[idx] = (x + 0.2, y + 0.2, z, v)
            user_frames.append(PoseFrame(timestamp=ref_frame.timestamp, keypoints=kp))

        pairs = _identity_pairs(num)
        result = scorer.score(pairs, ref, user_frames)

        # Manually compute weighted average
        js = result.joint_scores
        expected = (
            js.left_arm.value * JOINT_WEIGHTS["left_arm"]
            + js.right_arm.value * JOINT_WEIGHTS["right_arm"]
            + js.left_leg.value * JOINT_WEIGHTS["left_leg"]
            + js.right_leg.value * JOINT_WEIGHTS["right_leg"]
            + js.torso.value * JOINT_WEIGHTS["torso"]
            + js.head.value * JOINT_WEIGHTS["head"]
        )

        assert abs(result.overall_score.value - round(expected, 2)) < 0.01


class TestDistanceToScore:
    """Unit tests for the distance-to-score mapping function."""

    def test_zero_distance_is_100(self) -> None:
        assert _distance_to_score(0.0) == 100.0

    def test_max_distance_is_0(self) -> None:
        assert _distance_to_score(0.3) == 0.0

    def test_above_max_is_0(self) -> None:
        assert _distance_to_score(1.0) == 0.0

    def test_midpoint(self) -> None:
        # 0.15 is halfway => score should be ~50
        score = _distance_to_score(0.15)
        assert abs(score - 50.0) < 0.01

    def test_negative_distance_is_100(self) -> None:
        # Negative distance (shouldn't happen but handle gracefully)
        assert _distance_to_score(-0.1) == 100.0


class TestScorerEmptyInput:
    """Scorer handles empty aligned pairs."""

    def test_empty_aligned_pairs(self) -> None:
        scorer = DanceScorer()
        result = scorer.score([], [], [])

        assert result.overall_score.value == 0.0
        assert "No aligned frames" in result.feedback[0]
