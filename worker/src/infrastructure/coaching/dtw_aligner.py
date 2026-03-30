"""DTW-based temporal alignment for dance pose sequences.

Implements Dynamic Time Warping using numpy for efficient computation
of the optimal alignment between a reference choreography and a user's
dance performance.
"""
from __future__ import annotations

import logging

import numpy as np
from scipy.spatial.distance import cdist

from src.application.ports.coaching import DanceAligner, DTWResult
from src.domain.value_objects import PoseFrame

logger = logging.getLogger(__name__)

_DOWNSAMPLE_THRESHOLD = 1000
_DOWNSAMPLE_STEP = 3


class DTWAligner(DanceAligner):
    """Aligns two pose sequences using Dynamic Time Warping.

    Flattens each PoseFrame to a 99-dimensional vector (33 joints * 3
    coordinates, excluding visibility) and computes the optimal warping
    path that minimizes cumulative Euclidean distance.

    For sequences longer than 1000 frames, automatic downsampling
    is applied (every 3rd frame) to keep computation tractable.
    """

    def align(
        self,
        reference: list[PoseFrame],
        user: list[PoseFrame],
    ) -> DTWResult:
        """Compute DTW alignment between reference and user pose sequences.

        Args:
            reference: Reference choreography pose sequence.
            user: User's dance performance pose sequence.

        Returns:
            DTWResult with aligned frame pairs and distance metrics.
        """
        if not reference or not user:
            return DTWResult(
                aligned_pairs=[],
                total_distance=0.0,
                normalized_distance=0.0,
            )

        ref_frames = reference
        user_frames = user
        ref_indices = list(range(len(reference)))
        user_indices = list(range(len(user)))

        # Downsample long sequences to keep DTW computation feasible
        downsampled = False
        if len(reference) > _DOWNSAMPLE_THRESHOLD or len(user) > _DOWNSAMPLE_THRESHOLD:
            logger.info(
                "Downsampling sequences: ref=%d, user=%d (threshold=%d)",
                len(reference),
                len(user),
                _DOWNSAMPLE_THRESHOLD,
            )
            ref_indices = list(range(0, len(reference), _DOWNSAMPLE_STEP))
            user_indices = list(range(0, len(user), _DOWNSAMPLE_STEP))
            ref_frames = [reference[i] for i in ref_indices]
            user_frames = [user[i] for i in user_indices]
            downsampled = True

        # Flatten pose frames to feature vectors
        ref_matrix = np.array(
            [frame.to_flat_vector() for frame in ref_frames],
            dtype=np.float64,
        )
        user_matrix = np.array(
            [frame.to_flat_vector() for frame in user_frames],
            dtype=np.float64,
        )

        n = len(ref_matrix)
        m = len(user_matrix)

        # Compute pairwise Euclidean distance matrix
        dist_matrix = cdist(ref_matrix, user_matrix, metric="euclidean")

        # Build DTW accumulated cost matrix
        cost = np.full((n + 1, m + 1), np.inf, dtype=np.float64)
        cost[0, 0] = 0.0

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost[i, j] = dist_matrix[i - 1, j - 1] + min(
                    cost[i - 1, j],      # insertion
                    cost[i, j - 1],      # deletion
                    cost[i - 1, j - 1],  # match
                )

        total_distance = float(cost[n, m])

        # Backtrack to find optimal alignment path
        path: list[tuple[int, int]] = []
        i, j = n, m
        while i > 0 and j > 0:
            path.append((i - 1, j - 1))
            candidates = [
                (cost[i - 1, j - 1], i - 1, j - 1),
                (cost[i - 1, j], i - 1, j),
                (cost[i, j - 1], i, j - 1),
            ]
            _, i, j = min(candidates, key=lambda x: x[0])

        path.reverse()

        # Map downsampled indices back to original indices
        if downsampled:
            aligned_pairs = [
                (ref_indices[ri], user_indices[ui]) for ri, ui in path
            ]
        else:
            aligned_pairs = path

        normalized_distance = (
            total_distance / len(aligned_pairs) if aligned_pairs else 0.0
        )

        logger.info(
            "DTW alignment complete: %d pairs, total_dist=%.4f, norm_dist=%.4f",
            len(aligned_pairs),
            total_distance,
            normalized_distance,
        )

        return DTWResult(
            aligned_pairs=aligned_pairs,
            total_distance=total_distance,
            normalized_distance=normalized_distance,
        )
