"""Port (interface) for pose extraction from video.

Defines the contract for extracting skeletal pose data from dance videos,
used by the coaching pipeline for movement comparison.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.domain.value_objects import PoseFrame


class PoseExtractor(ABC):
    """Abstract base class for pose extraction from video files.

    Implementations extract per-frame skeletal keypoints from video,
    producing a sequence of PoseFrame value objects suitable for
    movement analysis and comparison.
    """

    @abstractmethod
    def extract_from_video(self, video_path: Path) -> list[PoseFrame]:
        """Extract pose keypoints from every frame of a video.

        Args:
            video_path: Path to the input video file.

        Returns:
            A list of PoseFrame objects, one per video frame,
            ordered chronologically by timestamp.

        Raises:
            PipelineError: If video cannot be read or pose extraction fails.
            ValidationError: If the video file does not exist or is invalid.
        """
        ...
