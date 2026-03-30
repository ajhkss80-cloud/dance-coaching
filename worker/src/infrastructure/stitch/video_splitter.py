"""Video splitter utility for the stitch pipeline.

Splits a source video into segments at specified time boundaries
using FFmpeg with accurate seeking. This module delegates to the
``split_video`` function already defined in ``ffmpeg_stitcher`` but
provides a standalone entry point for clarity and testability.
"""
from __future__ import annotations

from pathlib import Path

from src.domain.entities import Segment
from src.infrastructure.stitch.ffmpeg_stitcher import split_video as _ffmpeg_split


def split_video(
    input_path: Path,
    segments: list[Segment],
    output_dir: Path,
) -> list[Path]:
    """Split a video into segments at the specified boundaries.

    Uses FFmpeg to extract each segment with accurate seeking.
    Segment files are named ``segment_XXXX.mp4`` where XXXX is
    the zero-padded segment index.

    Args:
        input_path: Path to the source video file.
        segments: List of Segment objects defining time boundaries.
        output_dir: Directory for output segment files.

    Returns:
        Ordered list of paths to the created segment files.

    Raises:
        ValidationError: If the input file does not exist.
        PipelineError: If any split operation fails.
    """
    return _ffmpeg_split(input_path, segments, output_dir)
