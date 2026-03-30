"""Use case for generating a dance tutorial video.

Accepts raw inputs, constructs domain entities, delegates to the
orchestrator, and returns a result dictionary suitable for the
infrastructure layer to serialize and return to callers.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from src.application.orchestrator import GenerationOrchestrator
from src.domain.entities import GenerateJob
from src.domain.errors import DomainError
from src.domain.value_objects import BackendType

logger = logging.getLogger(__name__)


class GenerateTutorialUseCase:
    """Generates a dance tutorial video from an avatar and reference choreography.

    This use case serves as the application-layer entry point for the
    video generation pipeline. It validates inputs, constructs domain
    entities, runs the orchestrator, and returns structured results.
    """

    def __init__(self, orchestrator: GenerationOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def execute(
        self,
        job_id: str,
        avatar_path: str,
        reference_path: str,
        backend_type: str,
        options: dict,
        progress_callback: Callable[[float], None] | None = None,
    ) -> dict:
        """Execute the tutorial generation pipeline.

        Args:
            job_id: Unique identifier for this generation job.
            avatar_path: File path to the avatar image.
            reference_path: File path to the reference dance video.
            backend_type: Backend type string ('cloud' or 'local').
            options: Additional backend-specific options.
            progress_callback: Optional callback for progress reporting.

        Returns:
            A dictionary containing:
                - job_id: The job identifier.
                - status: 'completed' or 'failed'.
                - output_path: Path to the generated video (on success).
                - error: Error message (on failure).
        """
        # Default no-op callback
        if progress_callback is None:
            progress_callback = lambda _: None  # noqa: E731

        # Validate backend type via value object
        backend_enum = BackendType.from_string(backend_type)

        # Construct domain entity
        job = GenerateJob(
            job_id=job_id,
            avatar_path=Path(avatar_path),
            reference_path=Path(reference_path),
            backend_type=backend_enum.value,
        )

        logger.info(
            "Starting tutorial generation: job_id=%s, backend=%s",
            job_id,
            backend_enum.value,
        )

        try:
            # Determine if we should skip stitching (Phase 3 not ready)
            skip_stitch = options.get("skip_stitch", True)

            output_path = await self._orchestrator.run(
                job=job,
                progress_callback=progress_callback,
                skip_stitch=skip_stitch,
            )

            job.complete()
            logger.info("Tutorial generation completed: job_id=%s", job_id)

            return {
                "job_id": job.job_id,
                "status": job.status,
                "output_path": str(output_path),
                "segments_count": len(job.segments),
            }

        except DomainError as exc:
            job.fail(exc.message)
            logger.error(
                "Tutorial generation failed: job_id=%s, error=%s",
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
                "Tutorial generation unexpected failure: job_id=%s", job_id
            )
            return {
                "job_id": job.job_id,
                "status": job.status,
                "error": error_msg,
                "error_code": "UNEXPECTED_ERROR",
            }
