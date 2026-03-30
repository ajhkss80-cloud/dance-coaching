"""Use case for coaching a dancer by comparing their performance to a reference.

Extracts pose data from both videos, aligns the sequences temporally,
scores per-joint accuracy, and returns actionable feedback.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from src.application.ports.coaching import DanceAligner, DanceScorerPort
from src.application.ports.pose_extractor import PoseExtractor
from src.domain.entities import CoachJob
from src.domain.errors import DomainError, ValidationError
from src.domain.value_objects import JointScores, PoseFrame, Score

logger = logging.getLogger(__name__)


class CoachDanceUseCase:
    """Analyzes a user's dance performance against a reference video.

    Extracts skeletal pose data from both videos, temporally aligns them
    using DTW (Dynamic Time Warping), and produces per-joint-group
    scoring with actionable feedback.
    """

    def __init__(
        self,
        pose_extractor: PoseExtractor,
        aligner: DanceAligner,
        scorer: DanceScorerPort,
    ) -> None:
        self._pose_extractor = pose_extractor
        self._aligner = aligner
        self._scorer = scorer

    async def execute(
        self,
        job_id: str,
        user_video: str,
        reference_video: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> dict:
        """Execute the dance coaching analysis pipeline.

        Args:
            job_id: Unique identifier for this coaching job.
            user_video: File path to the user's dance video.
            reference_video: File path to the reference dance video.
            progress_callback: Optional callback for progress reporting.

        Returns:
            A dictionary containing:
                - job_id: The job identifier.
                - status: 'completed' or 'failed'.
                - overall_score: Float score 0-100 (on success).
                - joint_scores: Dict of joint group scores (on success).
                - feedback: List of feedback strings (on success).
                - worst_segments: List of worst-performing time segments (on success).
                - error: Error message (on failure).
        """
        if progress_callback is None:
            progress_callback = lambda _: None  # noqa: E731

        user_path = Path(user_video)
        ref_path = Path(reference_video)

        job = CoachJob(
            job_id=job_id,
            user_video_path=user_path,
            reference_video_path=ref_path,
        )

        logger.info("Starting dance coaching analysis: job_id=%s", job_id)

        try:
            # Validate inputs
            if not user_path.exists():
                raise ValidationError(f"User video not found: {user_path}")
            if not ref_path.exists():
                raise ValidationError(f"Reference video not found: {ref_path}")

            # Step 1 (25%): Extract poses from reference video
            job.update_progress(5.0)
            progress_callback(5.0)
            reference_poses = self._pose_extractor.extract_from_video(ref_path)
            job.update_progress(25.0)
            progress_callback(25.0)
            logger.info(
                "Reference pose extraction complete: %d frames", len(reference_poses)
            )

            # Step 2 (50%): Extract poses from user video
            user_poses = self._pose_extractor.extract_from_video(user_path)
            job.update_progress(50.0)
            progress_callback(50.0)
            logger.info(
                "User pose extraction complete: %d frames", len(user_poses)
            )

            # Step 3 (75%): DTW alignment
            dtw_result = self._aligner.align(reference_poses, user_poses)
            job.update_progress(75.0)
            progress_callback(75.0)
            logger.info(
                "Temporal alignment complete: %d aligned pairs",
                len(dtw_result.aligned_pairs),
            )

            # Step 4 (100%): Score and generate feedback
            scoring_result = self._scorer.score(
                dtw_result.aligned_pairs, reference_poses, user_poses
            )

            job.complete()
            progress_callback(100.0)
            logger.info(
                "Coaching analysis complete: job_id=%s, score=%.1f",
                job_id,
                scoring_result.overall_score.value,
            )

            return {
                "job_id": job.job_id,
                "status": job.status,
                "overall_score": scoring_result.overall_score.value,
                "joint_scores": {
                    "left_arm": scoring_result.joint_scores.left_arm.value,
                    "right_arm": scoring_result.joint_scores.right_arm.value,
                    "left_leg": scoring_result.joint_scores.left_leg.value,
                    "right_leg": scoring_result.joint_scores.right_leg.value,
                    "torso": scoring_result.joint_scores.torso.value,
                    "head": scoring_result.joint_scores.head.value,
                },
                "feedback": scoring_result.feedback,
                "worst_segments": scoring_result.worst_segments,
            }

        except DomainError as exc:
            job.fail(exc.message)
            logger.error(
                "Coaching analysis failed: job_id=%s, error=%s",
                job_id,
                exc.message,
            )
            return {
                "job_id": job.job_id,
                "status": job.status,
                "error": exc.message,
                "error_code": exc.code,
            }

        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            job.fail(error_msg)
            logger.exception(
                "Coaching analysis unexpected failure: job_id=%s", job_id
            )
            return {
                "job_id": job.job_id,
                "status": job.status,
                "error": error_msg,
                "error_code": "UNEXPECTED_ERROR",
            }
