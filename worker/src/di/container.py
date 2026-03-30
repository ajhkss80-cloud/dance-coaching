"""Dependency injection container.

Wires together infrastructure implementations with application-layer
use cases based on the active configuration. Supports override
parameters for testing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.application.orchestrator import GenerationOrchestrator
from src.application.ports.audio_processor import AudioProcessor
from src.application.ports.generation_backend import GenerationBackend
from src.application.ports.coaching import DanceAligner, DanceScorerPort
from src.application.ports.pose_extractor import PoseExtractor
from src.application.ports.video_stitcher import FrameInterpolator, VideoStitcher
from src.application.use_cases.coach_dance import CoachDanceUseCase
from src.application.use_cases.generate_tutorial import GenerateTutorialUseCase
from src.infrastructure.config import WorkerConfig

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """Holds all wired application dependencies.

    Provides typed access to every component in the system. Created
    by ``create_container`` and not intended to be constructed directly.
    """

    config: WorkerConfig
    backend: GenerationBackend
    audio_processor: AudioProcessor
    pose_extractor: PoseExtractor
    aligner: DanceAligner
    scorer: DanceScorerPort
    stitcher: VideoStitcher
    interpolator: FrameInterpolator
    orchestrator: GenerationOrchestrator
    generate_use_case: GenerateTutorialUseCase
    coach_use_case: CoachDanceUseCase


def create_container(
    config: WorkerConfig | None = None,
    *,
    backend_override: GenerationBackend | None = None,
    audio_processor_override: AudioProcessor | None = None,
    pose_extractor_override: PoseExtractor | None = None,
    aligner_override: DanceAligner | None = None,
    scorer_override: DanceScorerPort | None = None,
    stitcher_override: VideoStitcher | None = None,
    interpolator_override: FrameInterpolator | None = None,
) -> Container:
    """Build the dependency graph from configuration.

    Selects the appropriate backend implementation based on
    ``config.GENERATION_BACKEND`` and wires all components together.

    Args:
        config: Application configuration. If ``None``, a new
            ``WorkerConfig`` is loaded from environment variables.
        backend_override: Optional backend to use instead of creating
            one from config. Useful for testing.
        audio_processor_override: Optional audio processor override.
        pose_extractor_override: Optional pose extractor override.
        stitcher_override: Optional video stitcher override.
        interpolator_override: Optional frame interpolator override.

    Returns:
        A fully wired ``Container`` with all dependencies.

    Raises:
        ValueError: If the configured backend type is unknown.
    """
    if config is None:
        config = WorkerConfig()

    # --- Backend ---
    if backend_override is not None:
        backend = backend_override
        logger.info("Using overridden backend: %s", backend.name())
    elif config.GENERATION_BACKEND == "cloud":
        from src.infrastructure.backends.kling_backend import KlingBackend

        backend = KlingBackend(
            api_key=config.KLING_API_KEY,
            base_url=config.KLING_API_BASE_URL,
        )
        logger.info("Created Kling cloud backend")
    elif config.GENERATION_BACKEND == "local":
        from src.infrastructure.backends.mimicmotion_backend import (
            MimicMotionBackend,
        )

        backend = MimicMotionBackend(
            model_dir=config.MIMICMOTION_MODEL_DIR,
            repo_dir=config.MIMICMOTION_REPO_DIR,
        )
        logger.info("Created MimicMotion local backend")
    else:
        raise ValueError(
            f"Unknown GENERATION_BACKEND: '{config.GENERATION_BACKEND}'"
        )

    # --- Audio Processor ---
    if audio_processor_override is not None:
        audio_processor = audio_processor_override
        logger.info("Using overridden audio processor")
    else:
        from src.infrastructure.audio.librosa_processor import LibrosaProcessor

        audio_processor = LibrosaProcessor()
        logger.info("Created LibrosaProcessor")

    # --- Pose Extractor ---
    if pose_extractor_override is not None:
        pose_extractor = pose_extractor_override
        logger.info("Using overridden pose extractor")
    else:
        from src.infrastructure.pose.mediapipe_extractor import (
            MediaPipeExtractor,
        )

        pose_extractor = MediaPipeExtractor()
        logger.info("Created MediaPipeExtractor")

    # --- Video Stitcher ---
    if stitcher_override is not None:
        stitcher = stitcher_override
        logger.info("Using overridden video stitcher")
    else:
        from src.infrastructure.stitch.ffmpeg_stitcher import FFmpegStitcher

        stitcher = FFmpegStitcher()
        logger.info("Created FFmpegStitcher")

    # --- Frame Interpolator ---
    if interpolator_override is not None:
        interpolator = interpolator_override
        logger.info("Using overridden frame interpolator")
    else:
        from src.infrastructure.stitch.rife_interpolator import RIFEInterpolator

        interpolator = RIFEInterpolator(
            model_dir=config.RIFE_MODEL_DIR,
            num_frames=config.RIFE_INTERPOLATION_FRAMES,
        )
        logger.info("Created RIFEInterpolator")

    # --- Dance Aligner ---
    if aligner_override is not None:
        aligner = aligner_override
        logger.info("Using overridden dance aligner")
    else:
        from src.infrastructure.coaching.dtw_aligner import DTWAligner

        aligner = DTWAligner()
        logger.info("Created DTWAligner")

    # --- Dance Scorer ---
    if scorer_override is not None:
        scorer = scorer_override
        logger.info("Using overridden dance scorer")
    else:
        from src.infrastructure.coaching.scorer import DanceScorer

        scorer = DanceScorer()
        logger.info("Created DanceScorer")

    # --- Orchestrator ---
    orchestrator = GenerationOrchestrator(
        backend=backend,
        audio_processor=audio_processor,
        stitcher=stitcher,
        interpolator=interpolator,
    )

    # --- Use Cases ---
    generate_use_case = GenerateTutorialUseCase(orchestrator=orchestrator)
    coach_use_case = CoachDanceUseCase(
        pose_extractor=pose_extractor,
        aligner=aligner,
        scorer=scorer,
    )

    container = Container(
        config=config,
        backend=backend,
        audio_processor=audio_processor,
        pose_extractor=pose_extractor,
        aligner=aligner,
        scorer=scorer,
        stitcher=stitcher,
        interpolator=interpolator,
        orchestrator=orchestrator,
        generate_use_case=generate_use_case,
        coach_use_case=coach_use_case,
    )

    logger.info(
        "DI container created (backend=%s)", config.GENERATION_BACKEND
    )

    return container
