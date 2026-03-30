"""MimicMotion local GPU backend for video generation.

Implements the GenerationBackend ABC using a locally-installed
MimicMotion model with DWPose for pose extraction. Requires a
CUDA-capable GPU with at least 14 GB of VRAM.
"""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

from src.application.ports.generation_backend import GenerationBackend
from src.domain.errors import BackendError, InsufficientResourceError

logger = logging.getLogger(__name__)

# Minimum usable VRAM in bytes (14 GB)
_MIN_VRAM_BYTES = 14 * 1024 * 1024 * 1024


class MimicMotionBackend(GenerationBackend):
    """Local GPU backend using the MimicMotion motion-transfer model.

    Loads the MimicMotion pipeline and DWPose model onto a CUDA GPU,
    then generates dance videos by transferring motion from a reference
    segment onto an avatar image.

    Attributes:
        model_dir: Path to the MimicMotion model weights directory.
        repo_dir: Path to the vendored MimicMotion repository.
    """

    def __init__(self, model_dir: str, repo_dir: str) -> None:
        self._model_dir = Path(model_dir)
        self._repo_dir = Path(repo_dir)
        self._pipeline = None
        self._dwpose = None

    async def initialize(self) -> None:
        """Load the MimicMotion pipeline and DWPose model.

        Validates GPU availability and VRAM capacity before loading.

        Raises:
            InsufficientResourceError: If no CUDA GPU or insufficient VRAM.
            BackendError: If model loading fails.
        """
        # Validate CUDA availability
        try:
            import torch
        except ImportError:
            raise BackendError(
                "PyTorch is not installed. "
                "Install with: pip install torch torchvision"
            )

        if not torch.cuda.is_available():
            raise InsufficientResourceError(
                "CUDA GPU is required for MimicMotion backend but none detected. "
                "Ensure NVIDIA drivers and CUDA toolkit are installed."
            )

        # Check VRAM
        device = torch.cuda.current_device()
        total_vram = torch.cuda.get_device_properties(device).total_mem
        if total_vram < _MIN_VRAM_BYTES:
            vram_gb = total_vram / (1024 ** 3)
            raise InsufficientResourceError(
                f"MimicMotion requires at least 14 GB VRAM, "
                f"but GPU has {vram_gb:.1f} GB"
            )

        vram_gb = total_vram / (1024 ** 3)
        gpu_name = torch.cuda.get_device_name(device)
        logger.info(
            "CUDA GPU detected: %s (%.1f GB VRAM)", gpu_name, vram_gb
        )

        # Add vendored repo to sys.path for imports
        repo_str = str(self._repo_dir)
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)
            logger.info("Added MimicMotion repo to sys.path: %s", repo_str)

        # Lazy-load MimicMotion pipeline
        try:
            from mimicmotion.pipelines.pipeline_mimicmotion import (
                MimicMotionPipeline,
            )

            self._pipeline = MimicMotionPipeline.from_pretrained(
                str(self._model_dir),
                torch_dtype=torch.float16,
            ).to("cuda")

            logger.info("MimicMotion pipeline loaded from %s", self._model_dir)
        except ImportError:
            raise BackendError(
                f"MimicMotion module not found in {self._repo_dir}. "
                "Ensure the repository is cloned to the configured "
                "MIMICMOTION_REPO_DIR path."
            )
        except Exception as exc:
            raise BackendError(f"Failed to load MimicMotion pipeline: {exc}")

        # Load DWPose for reference pose extraction
        try:
            from mimicmotion.dwpose import DWposeDetector

            self._dwpose = DWposeDetector()
            logger.info("DWPose detector loaded")
        except ImportError:
            raise BackendError(
                "DWPose module not found in MimicMotion repository. "
                "Verify the vendored repo structure."
            )
        except Exception as exc:
            raise BackendError(f"Failed to load DWPose detector: {exc}")

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Generate a video segment using local GPU inference.

        Extracts the motion pose sequence from the reference segment
        using DWPose, then runs the MimicMotion pipeline to transfer
        that motion onto the avatar image.

        Args:
            avatar_path: Path to the avatar image file.
            segment_path: Path to the reference video segment.
            segment_index: Zero-based index of this segment.
            options: Additional options (currently unused).

        Returns:
            Path to the generated video segment.

        Raises:
            BackendError: If generation fails.
            InsufficientResourceError: On GPU OOM.
        """
        if self._pipeline is None or self._dwpose is None:
            raise BackendError(
                "Backend not initialised. Call initialize() first."
            )

        try:
            import torch
            import cv2
            import numpy as np
            from PIL import Image
        except ImportError as exc:
            raise BackendError(f"Missing required dependency: {exc}")

        logger.info("Generating segment %d via MimicMotion (local GPU)", segment_index)

        try:
            # Step 1: Extract pose sequence from reference segment
            cap = cv2.VideoCapture(str(segment_path))
            if not cap.isOpened():
                raise BackendError(f"Cannot open segment video: {segment_path}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            pose_frames = []

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pose = self._dwpose(Image.fromarray(rgb))
                    pose_frames.append(pose)
            finally:
                cap.release()

            if not pose_frames:
                raise BackendError(
                    f"No frames extracted from segment {segment_index}"
                )

            logger.info(
                "Extracted %d pose frames from segment %d",
                len(pose_frames), segment_index,
            )

            # Step 2: Load avatar image
            avatar_img = Image.open(str(avatar_path)).convert("RGB")

            # Step 3: Run MimicMotion inference
            with torch.inference_mode():
                result = self._pipeline(
                    image=avatar_img,
                    pose_sequence=pose_frames,
                    num_inference_steps=25,
                )

            # Step 4: Save output frames as video
            output_path = Path(tempfile.mktemp(
                suffix=".mp4",
                prefix=f"mimic_seg{segment_index}_",
            ))

            output_frames = result.frames if hasattr(result, "frames") else result
            if not output_frames:
                raise BackendError(
                    f"MimicMotion produced no frames for segment {segment_index}"
                )

            # Convert PIL images to video
            first_frame = np.array(output_frames[0])
            h, w = first_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

            try:
                for frame in output_frames:
                    bgr = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
                    writer.write(bgr)
            finally:
                writer.release()

            # Step 5: Clear GPU cache
            torch.cuda.empty_cache()

            logger.info(
                "Segment %d generated: %s (%d frames)",
                segment_index, output_path, len(output_frames),
            )

            return output_path

        except (BackendError, InsufficientResourceError):
            raise
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                import torch
                torch.cuda.empty_cache()
                raise InsufficientResourceError(
                    f"GPU out of memory generating segment {segment_index}: {exc}"
                )
            raise BackendError(
                f"Runtime error generating segment {segment_index}: {exc}"
            )
        except Exception as exc:
            raise BackendError(
                f"Unexpected error generating segment {segment_index}: {exc}"
            )

    async def cleanup(self) -> None:
        """Release the GPU model and free VRAM."""
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None

        if self._dwpose is not None:
            del self._dwpose
            self._dwpose = None

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        logger.info("MimicMotion backend cleaned up")

    def name(self) -> str:
        """Return the backend name."""
        return "mimicmotion-local"
