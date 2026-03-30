"""Port (interface) for audio processing operations.

Defines the contract for audio extraction, beat detection, and
duration measurement -- used to segment dance videos at musically
meaningful boundaries.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class AudioProcessor(ABC):
    """Abstract base class for audio processing operations.

    Implementations handle audio extraction from video, beat detection
    for segment boundary alignment, and duration measurement.
    """

    @abstractmethod
    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        """Extract the audio track from a video file.

        Args:
            video_path: Path to the input video file.
            output_path: Path where the extracted audio should be written.

        Returns:
            Path to the extracted audio file (same as output_path on success).

        Raises:
            PipelineError: If audio extraction fails.
            ValidationError: If the video file does not exist or has no audio.
        """
        ...

    @abstractmethod
    def detect_beats(self, audio_path: Path) -> list[float]:
        """Detect beat timestamps in an audio file.

        Args:
            audio_path: Path to the audio file to analyze.

        Returns:
            A sorted list of beat timestamps in seconds.

        Raises:
            PipelineError: If beat detection fails.
        """
        ...

    @abstractmethod
    def get_duration(self, video_path: Path) -> float:
        """Get the duration of a video file in seconds.

        Args:
            video_path: Path to the video file.

        Returns:
            Duration in seconds as a float.

        Raises:
            PipelineError: If the video cannot be read.
            ValidationError: If the file does not exist.
        """
        ...
