"""BullMQ Python worker entry point.

Listens on Redis-backed queues for generation and coaching jobs,
dispatching each to the appropriate application-layer use case.
Provides progress reporting back through BullMQ job updates.
"""
from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from src.application.use_cases.coach_dance import CoachDanceUseCase
from src.application.use_cases.generate_tutorial import GenerateTutorialUseCase

logger = logging.getLogger(__name__)

GENERATE_QUEUE = "generate-queue"
COACH_QUEUE = "coach-queue"


class BullMQWorker:
    """Async worker that processes jobs from BullMQ queues.

    Routes incoming jobs to the appropriate use case based on queue
    name, and reports progress through BullMQ's job update mechanism.

    Attributes:
        generate_use_case: Handler for generation jobs.
        coach_use_case: Handler for coaching analysis jobs.
        redis_url: Redis connection URL for BullMQ.
        concurrency: Maximum number of concurrent jobs.
    """

    def __init__(
        self,
        generate_use_case: GenerateTutorialUseCase,
        coach_use_case: CoachDanceUseCase,
        redis_url: str = "redis://localhost:6379",
        concurrency: int = 1,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._coach_use_case = coach_use_case
        self._redis_url = redis_url
        self._concurrency = concurrency
        self._workers: list[Any] = []
        self._running = False

    async def start(self) -> None:
        """Start listening on both queues.

        Creates BullMQ Worker instances for the generation and
        coaching queues and begins processing jobs. Blocks until
        ``stop()`` is called or a shutdown signal is received.

        Raises:
            RuntimeError: If bullmq package is not installed.
        """
        try:
            from bullmq import Worker
        except ImportError:
            raise RuntimeError(
                "bullmq is not installed. Install with: pip install bullmq"
            )

        self._running = True

        logger.info(
            "Starting BullMQ workers (redis=%s, concurrency=%d)",
            self._redis_url, self._concurrency,
        )

        generate_worker = Worker(
            GENERATE_QUEUE,
            self._process_generate_job,
            {
                "connection": self._redis_url,
                "concurrency": self._concurrency,
            },
        )

        coach_worker = Worker(
            COACH_QUEUE,
            self._process_coach_job,
            {
                "connection": self._redis_url,
                "concurrency": self._concurrency,
            },
        )

        self._workers = [generate_worker, coach_worker]

        logger.info(
            "Workers started on queues: %s, %s",
            GENERATE_QUEUE, COACH_QUEUE,
        )

        # Block until shutdown is requested
        while self._running:
            await asyncio.sleep(1.0)

    async def stop(self) -> None:
        """Gracefully stop all workers.

        Allows in-progress jobs to complete, then closes the workers.
        """
        self._running = False

        for worker in self._workers:
            try:
                await worker.close()
            except Exception as exc:
                logger.warning("Error closing worker: %s", exc)

        self._workers.clear()
        logger.info("BullMQ workers stopped")

    async def _process_generate_job(self, job: Any, token: str) -> dict:
        """Process a single generation job from the queue.

        Args:
            job: BullMQ job object with data and progress methods.
            token: Worker lock token.

        Returns:
            Result dictionary from the use case.
        """
        data = job.data
        job_id = data.get("job_id", job.id)

        logger.info("Processing generate job: %s", job_id)

        async def progress_callback(value: float) -> None:
            try:
                await job.updateProgress(int(value))
            except Exception as exc:
                logger.warning(
                    "Failed to update progress for %s: %s", job_id, exc
                )

        result = await self._generate_use_case.execute(
            job_id=job_id,
            avatar_path=data["avatar_path"],
            reference_path=data["reference_path"],
            backend_type=data.get("backend_type", "cloud"),
            options=data.get("options", {}),
            progress_callback=progress_callback,
        )

        logger.info(
            "Generate job %s completed with status: %s",
            job_id, result.get("status"),
        )

        return result

    async def _process_coach_job(self, job: Any, token: str) -> dict:
        """Process a single coaching job from the queue.

        Args:
            job: BullMQ job object with data and progress methods.
            token: Worker lock token.

        Returns:
            Result dictionary from the use case.
        """
        data = job.data
        job_id = data.get("job_id", job.id)

        logger.info("Processing coach job: %s", job_id)

        async def progress_callback(value: float) -> None:
            try:
                await job.updateProgress(int(value))
            except Exception as exc:
                logger.warning(
                    "Failed to update progress for %s: %s", job_id, exc
                )

        result = await self._coach_use_case.execute(
            job_id=job_id,
            user_video=data["user_video_path"],
            reference_video=data["reference_video_path"],
            progress_callback=progress_callback,
        )

        logger.info(
            "Coach job %s completed with status: %s",
            job_id, result.get("status"),
        )

        return result
