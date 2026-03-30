"""Ports (interfaces) for video stitching and frame interpolation.

Defines the contracts for concatenating video segments, muxing audio,
and smoothing boundary transitions via frame interpolation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VideoStitcher(ABC):
    """Abstract base class for video stitching operations.

    Implementations concatenate multiple video segments into a single
    video and mux audio tracks onto the final result.
    """

    @abstractmethod
    def concat_segments(
        self,
        segment_paths: list[Path],
        output_path: Path,
        fps: int = 30,
    ) -> Path:
        """Concatenate multiple video segments into a single video.

        Args:
            segment_paths: Ordered list of segment video file paths.
            output_path: Path for the concatenated output file.
            fps: Output frame rate.

        Returns:
            Path to the concatenated output file.

        Raises:
            PipelineError: If concatenation fails or no segments provided.
        """
        ...

    @abstractmethod
    def mux_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        """Combine a video file with an audio file.

        Replaces any existing audio in the video with the provided
        audio track.

        Args:
            video_path: Path to the video file.
            audio_path: Path to the audio file to mux in.
            output_path: Path for the combined output file.

        Returns:
            Path to the muxed output file.

        Raises:
            PipelineError: If muxing fails.
            ValidationError: If input files do not exist.
        """
        ...


class FrameInterpolator(ABC):
    """Abstract base class for frame interpolation at segment boundaries.

    Implementations generate intermediate frames between the end of
    one video segment and the start of the next, producing smoother
    visual transitions.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the interpolator, loading models if necessary.

        May fall back to simpler methods (e.g. linear blend) if
        model weights are not available.
        """
        ...

    @abstractmethod
    def interpolate_boundary(
        self,
        seg_a_path: Path,
        seg_b_path: Path,
        num_frames: int = 2,
    ) -> list[Path]:
        """Generate intermediate frames between two video segments.

        Extracts the last frame of seg_a_path and the first frame
        of seg_b_path, then generates num_frames intermediate frames.

        Args:
            seg_a_path: Path to the first video segment.
            seg_b_path: Path to the second video segment.
            num_frames: Number of intermediate frames to generate.

        Returns:
            List of paths to the generated intermediate frame images.

        Raises:
            PipelineError: If frame extraction or interpolation fails.
        """
        ...
