"""RIFE frame interpolator for smooth segment boundary transitions.

Provides a linear-blend fallback for frame interpolation at segment
boundaries. The actual RIFE neural network model can be loaded later
to replace the linear blend with learned optical-flow interpolation.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from src.application.ports.video_stitcher import FrameInterpolator
from src.domain.errors import PipelineError

logger = logging.getLogger(__name__)


class RIFEInterpolator(FrameInterpolator):
    """Frame interpolator for smooth segment boundary transitions.

    Currently uses a simple linear alpha-blend between the last frame
    of one segment and the first frame of the next. A RIFE model
    can be loaded via ``initialize()`` to replace the blend with
    neural-network-based optical flow interpolation.

    Attributes:
        model_dir: Directory containing RIFE model weights.
        num_frames: Number of intermediate frames to generate.
    """

    def __init__(
        self,
        model_dir: str = "./models/rife",
        num_frames: int = 2,
    ) -> None:
        self._model_dir = Path(model_dir)
        self._num_frames = num_frames
        self._model_loaded = False

    def initialize(self) -> None:
        """Attempt to load the RIFE model weights.

        Falls back to linear blend if model weights are not available.
        This is not an error condition -- the blend fallback produces
        acceptable results for initial development.
        """
        model_path = self._model_dir / "flownet.pkl"
        if model_path.exists():
            logger.info("RIFE model found at %s (loading deferred)", model_path)
            self._model_loaded = True
        else:
            logger.info(
                "RIFE model not found at %s; using linear blend fallback",
                self._model_dir,
            )
            self._model_loaded = False

    def interpolate_boundary(
        self,
        seg_a_path: Path,
        seg_b_path: Path,
        num_frames: int | None = None,
    ) -> list[Path]:
        """Generate intermediate frames between two video segments.

        Extracts the last frame of ``seg_a_path`` and the first frame
        of ``seg_b_path``, then generates ``num_frames`` intermediate
        frames using linear alpha blending.

        Args:
            seg_a_path: Path to the first video segment.
            seg_b_path: Path to the second video segment.
            num_frames: Number of intermediate frames to generate.
                Defaults to the instance-level setting.

        Returns:
            List of paths to the generated intermediate frame images.

        Raises:
            PipelineError: If frame extraction or blending fails.
        """
        n = num_frames if num_frames is not None else self._num_frames

        try:
            import cv2
            import numpy as np
        except ImportError:
            raise PipelineError(
                "opencv-python and numpy are required for interpolation. "
                "Install with: pip install opencv-python-headless numpy"
            )

        last_frame = self._extract_last_frame(seg_a_path, cv2)
        first_frame = self._extract_first_frame(seg_b_path, cv2)

        # Ensure both frames have the same dimensions
        if last_frame.shape != first_frame.shape:
            h = min(last_frame.shape[0], first_frame.shape[0])
            w = min(last_frame.shape[1], first_frame.shape[1])
            last_frame = cv2.resize(last_frame, (w, h))
            first_frame = cv2.resize(first_frame, (w, h))

        output_dir = Path(tempfile.mkdtemp(prefix="rife_interp_"))
        output_paths: list[Path] = []

        for i in range(n):
            alpha = (i + 1) / (n + 1)
            blended = cv2.addWeighted(
                last_frame, 1.0 - alpha,
                first_frame, alpha,
                0.0,
            )
            frame_path = output_dir / f"interp_{i:04d}.png"
            cv2.imwrite(str(frame_path), blended)
            output_paths.append(frame_path)

        logger.info(
            "Generated %d interpolation frames between %s and %s",
            n, seg_a_path.name, seg_b_path.name,
        )

        return output_paths

    def _extract_last_frame(self, video_path: Path, cv2_module: object) -> object:
        """Extract the last frame from a video file.

        Args:
            video_path: Path to the video.
            cv2_module: The cv2 module (passed to avoid re-importing).

        Returns:
            The last frame as a numpy BGR array.

        Raises:
            PipelineError: If the video cannot be read.
        """
        cv2 = cv2_module  # type: ignore[assignment]

        if not video_path.exists():
            raise PipelineError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise PipelineError(f"Cannot open video: {video_path}")

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames > 1:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)

            ret, frame = cap.read()
            if not ret or frame is None:
                raise PipelineError(
                    f"Failed to read last frame from {video_path}"
                )
            return frame
        finally:
            cap.release()

    def _extract_first_frame(self, video_path: Path, cv2_module: object) -> object:
        """Extract the first frame from a video file.

        Args:
            video_path: Path to the video.
            cv2_module: The cv2 module (passed to avoid re-importing).

        Returns:
            The first frame as a numpy BGR array.

        Raises:
            PipelineError: If the video cannot be read.
        """
        cv2 = cv2_module  # type: ignore[assignment]

        if not video_path.exists():
            raise PipelineError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise PipelineError(f"Cannot open video: {video_path}")

        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                raise PipelineError(
                    f"Failed to read first frame from {video_path}"
                )
            return frame
        finally:
            cap.release()

    @property
    def model_loaded(self) -> bool:
        """Whether the RIFE neural network model is loaded."""
        return self._model_loaded
