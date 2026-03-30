"""Unit tests for the DTW aligner."""
from __future__ import annotations

import math
from math import sin

import pytest

from src.domain.value_objects import PoseFrame
from src.infrastructure.coaching.dtw_aligner import DTWAligner


def _make_pose_frame(timestamp: float, offset: float = 0.0) -> PoseFrame:
    """Create a PoseFrame with sine-wave keypoints shifted by offset."""
    keypoints = []
    for j in range(33):
        x = 0.5 + 0.1 * sin(timestamp * 2.0 + j * 0.1 + offset)
        y = 0.5 + 0.05 * j / 33.0 + 0.02 * sin(timestamp + offset)
        z = 0.0
        visibility = 0.99
        keypoints.append((x, y, z, visibility))
    return PoseFrame(timestamp=timestamp, keypoints=keypoints)


def _make_sequence(
    num_frames: int,
    fps: float = 30.0,
    offset: float = 0.0,
) -> list[PoseFrame]:
    """Generate a sequence of PoseFrames."""
    return [_make_pose_frame(i / fps, offset=offset) for i in range(num_frames)]


class TestDTWIdenticalSequences:
    """DTW alignment of identical sequences should produce near-zero distance."""

    def test_dtw_identical_sequences(self) -> None:
        aligner = DTWAligner()
        seq = _make_sequence(30)

        result = aligner.align(seq, seq)

        assert result.total_distance < 1e-6
        assert result.normalized_distance < 1e-6
        assert len(result.aligned_pairs) >= 30

    def test_dtw_identical_all_pairs_diagonal(self) -> None:
        """Identical sequences should produce diagonal alignment."""
        aligner = DTWAligner()
        seq = _make_sequence(20)

        result = aligner.align(seq, seq)

        # Diagonal means (i, i) for each frame
        for ref_idx, user_idx in result.aligned_pairs:
            assert ref_idx == user_idx


class TestDTWReversedSequence:
    """DTW with reversed sequences should have higher distance than identical."""

    def test_dtw_reversed_sequence(self) -> None:
        aligner = DTWAligner()
        seq = _make_sequence(30)
        reversed_seq = list(reversed(seq))
        # Fix timestamps so they are valid (non-decreasing)
        reversed_with_ts = [
            PoseFrame(timestamp=i / 30.0, keypoints=frame.keypoints)
            for i, frame in enumerate(reversed_seq)
        ]

        identical_result = aligner.align(seq, seq)
        reversed_result = aligner.align(seq, reversed_with_ts)

        assert reversed_result.total_distance > identical_result.total_distance


class TestDTWDifferentLengths:
    """DTW handles sequences of different lengths."""

    def test_dtw_different_lengths(self) -> None:
        aligner = DTWAligner()
        short_seq = _make_sequence(20)
        long_seq = _make_sequence(50)

        result = aligner.align(short_seq, long_seq)

        # Should produce alignment pairs
        assert len(result.aligned_pairs) > 0
        # All reference indices should be valid
        for ref_idx, user_idx in result.aligned_pairs:
            assert 0 <= ref_idx < 20
            assert 0 <= user_idx < 50

    def test_dtw_single_frame_sequences(self) -> None:
        aligner = DTWAligner()
        one_frame = _make_sequence(1)

        result = aligner.align(one_frame, one_frame)

        assert len(result.aligned_pairs) == 1
        assert result.aligned_pairs[0] == (0, 0)

    def test_dtw_one_vs_many(self) -> None:
        """One reference frame aligned to many user frames."""
        aligner = DTWAligner()
        one = _make_sequence(1)
        many = _make_sequence(10)

        result = aligner.align(one, many)

        assert len(result.aligned_pairs) >= 1
        # The single ref frame should be in at least one pair
        ref_indices = {pair[0] for pair in result.aligned_pairs}
        assert 0 in ref_indices


class TestDTWAlignedPairsCoverage:
    """Every frame should appear in at least one aligned pair."""

    def test_dtw_aligned_pairs_cover_all_frames(self) -> None:
        aligner = DTWAligner()
        ref = _make_sequence(25)
        user = _make_sequence(30)

        result = aligner.align(ref, user)

        ref_covered = {pair[0] for pair in result.aligned_pairs}
        user_covered = {pair[1] for pair in result.aligned_pairs}

        # Every reference frame should be covered
        assert ref_covered == set(range(25))
        # Every user frame should be covered
        assert user_covered == set(range(30))


class TestDTWDownsampling:
    """Long sequences trigger downsampling for performance."""

    def test_dtw_downsampling_for_long_sequences(self) -> None:
        aligner = DTWAligner()
        # Create sequences above the 1000-frame threshold
        long_ref = _make_sequence(1200, fps=30.0)
        long_user = _make_sequence(1100, fps=30.0)

        result = aligner.align(long_ref, long_user)

        # Alignment should still produce results
        assert len(result.aligned_pairs) > 0
        assert result.total_distance >= 0.0

        # Downsampled pairs use original indices (multiples of 3)
        for ref_idx, user_idx in result.aligned_pairs:
            assert ref_idx % 3 == 0
            assert user_idx % 3 == 0

    def test_dtw_no_downsampling_below_threshold(self) -> None:
        """Sequences below threshold are not downsampled."""
        aligner = DTWAligner()
        ref = _make_sequence(50)
        user = _make_sequence(50)

        result = aligner.align(ref, user)

        # All indices should be present (not just multiples of 3)
        ref_indices = {pair[0] for pair in result.aligned_pairs}
        assert ref_indices == set(range(50))


class TestDTWEmptyInputs:
    """Edge cases with empty inputs."""

    def test_dtw_empty_reference(self) -> None:
        aligner = DTWAligner()
        result = aligner.align([], _make_sequence(10))
        assert result.aligned_pairs == []
        assert result.total_distance == 0.0

    def test_dtw_empty_user(self) -> None:
        aligner = DTWAligner()
        result = aligner.align(_make_sequence(10), [])
        assert result.aligned_pairs == []

    def test_dtw_both_empty(self) -> None:
        aligner = DTWAligner()
        result = aligner.align([], [])
        assert result.aligned_pairs == []
        assert result.normalized_distance == 0.0
