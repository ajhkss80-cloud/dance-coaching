"""Worker entry point for the Dance Coaching Platform.

Loads configuration, builds the DI container, initialises the
generation backend, and starts BullMQ workers for processing
generation and coaching jobs from Redis queues.
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from src.di.container import create_container
from src.infrastructure.config import WorkerConfig
from src.infrastructure.queue.bullmq_worker import BullMQWorker

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Set up structured logging to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


async def _run() -> None:
    """Async main loop: build container, init backend, run workers."""
    config = WorkerConfig()
    container = create_container(config)

    # Initialise the generation backend (loads models / tests API)
    logger.info("Initialising backend: %s", container.backend.name())
    await container.backend.initialize()

    # Build and start the BullMQ worker
    worker = BullMQWorker(
        generate_use_case=container.generate_use_case,
        coach_use_case=container.coach_use_case,
        redis_url=config.REDIS_URL,
        concurrency=config.WORKER_CONCURRENCY,
    )

    # Register graceful shutdown on SIGINT and SIGTERM
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Signal handlers are not supported on Windows event loops
            # for SIGTERM; SIGINT is handled by KeyboardInterrupt
            pass

    # Start workers in background
    worker_task = asyncio.create_task(worker.start())

    logger.info(
        "Worker running (backend=%s, concurrency=%d, redis=%s)",
        config.GENERATION_BACKEND,
        config.WORKER_CONCURRENCY,
        config.REDIS_URL,
    )

    try:
        # Wait for shutdown signal or KeyboardInterrupt
        await shutdown_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupted, shutting down")
    finally:
        logger.info("Stopping workers...")
        await worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        logger.info("Cleaning up backend...")
        await container.backend.cleanup()

    logger.info("Worker shutdown complete")


def main() -> None:
    """Synchronous entry point."""
    _configure_logging()
    logger.info("Dance Coaching Worker starting")

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt")
    except Exception:
        logger.exception("Worker crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
