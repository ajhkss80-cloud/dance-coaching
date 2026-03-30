"""Fake audio processor for testing.

Provides a controllable test double that returns predetermined
beat times and durations without requiring actual audio processing.
"""
from __future__ import annotations

from pathlib import Path

from src.application.ports.audio_processor import AudioProcessor


class FakeAudioProcessor(AudioProcessor):
    """In-memory test double for AudioProcessor.

    Returns configurable beat times and duration values for
    deterministic testing of the orchestration pipeline.

    Attributes:
        beat_times: List of beat timestamps to return.
        duration: Video duration to report.
    """

    def __init__(
        self,
        beat_times: list[float] | None = None,
        duration: float = 30.0,
    ) -> None:
        self.beat_times = beat_times if beat_times is not None else [
            0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
            5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0,
            10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0,
        ]
        self.duration = duration

    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        """Create a placeholder audio file.

        Args:
            video_path: Path to the source video.
            output_path: Path to write the audio file.

        Returns:
            The output path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"FAKE_AUDIO_DATA")
        return output_path

    def detect_beats(self, audio_path: Path) -> list[float]:
        """Return the configured beat times.

        Args:
            audio_path: Path to the audio file (not read in fake).

        Returns:
            A sorted list of beat timestamps.
        """
        return sorted(self.beat_times)

    def get_duration(self, video_path: Path) -> float:
        """Return the configured duration.

        Args:
            video_path: Path to the video file (not read in fake).

        Returns:
            The configured duration in seconds.
        """
        return self.duration
