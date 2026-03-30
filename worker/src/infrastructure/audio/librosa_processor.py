"""Librosa-based audio processor implementation.

Uses FFmpeg for audio extraction and librosa for beat detection,
providing musically-meaningful segment boundaries for the
video generation pipeline.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from src.application.ports.audio_processor import AudioProcessor
from src.domain.errors import PipelineError, ValidationError

logger = logging.getLogger(__name__)


class LibrosaProcessor(AudioProcessor):
    """Audio processor using FFmpeg and librosa.

    Extracts audio from video files using FFmpeg subprocess calls
    and detects beats using librosa's beat tracking algorithm.
    """

    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        """Extract audio from a video file as mono WAV at 22050 Hz.

        Uses FFmpeg to demux and convert the audio stream to a
        standardised format suitable for librosa analysis.

        Args:
            video_path: Path to the source video file.
            output_path: Path where the extracted WAV should be written.

        Returns:
            Path to the extracted audio file.

        Raises:
            ValidationError: If the video file does not exist.
            PipelineError: If FFmpeg fails or the video has no audio.
        """
        if not video_path.exists():
            raise ValidationError(f"Video file not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "22050",
            "-ac", "1",
            str(output_path),
        ]

        logger.info("Extracting audio: %s -> %s", video_path, output_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except FileNotFoundError:
            raise PipelineError(
                "FFmpeg not found. Ensure FFmpeg is installed and on PATH."
            )
        except subprocess.TimeoutExpired:
            raise PipelineError(
                f"FFmpeg audio extraction timed out for {video_path}"
            )

        if result.returncode != 0:
            stderr_tail = result.stderr[-500:] if result.stderr else "(no stderr)"
            raise PipelineError(
                f"FFmpeg audio extraction failed (code {result.returncode}): "
                f"{stderr_tail}"
            )

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PipelineError(
                f"Audio extraction produced no output for {video_path}. "
                "The video may have no audio track."
            )

        logger.info(
            "Audio extracted: %s (%.1f KB)",
            output_path,
            output_path.stat().st_size / 1024,
        )
        return output_path

    def detect_beats(self, audio_path: Path) -> list[float]:
        """Detect beat timestamps using librosa beat tracking.

        Loads the audio file and runs librosa's beat detection
        algorithm, returning beat positions in seconds.

        Args:
            audio_path: Path to the WAV audio file.

        Returns:
            Sorted list of beat timestamps in seconds.

        Raises:
            PipelineError: If the audio cannot be loaded or beat
                detection fails.
        """
        if not audio_path.exists():
            raise PipelineError(f"Audio file not found: {audio_path}")

        try:
            import librosa
        except ImportError:
            raise PipelineError(
                "librosa is not installed. "
                "Install with: pip install librosa"
            )

        logger.info("Detecting beats in %s", audio_path)

        try:
            y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        except Exception as exc:
            raise PipelineError(
                f"Failed to load audio file {audio_path}: {exc}"
            )

        try:
            _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        except Exception as exc:
            raise PipelineError(f"Beat detection failed: {exc}")

        beat_list = sorted(float(t) for t in beat_times)

        logger.info(
            "Detected %d beats in %s (first=%.2f, last=%.2f)",
            len(beat_list),
            audio_path,
            beat_list[0] if beat_list else 0.0,
            beat_list[-1] if beat_list else 0.0,
        )

        return beat_list

    def get_duration(self, video_path: Path) -> float:
        """Get the duration of a video file using ffprobe.

        Args:
            video_path: Path to the video file.

        Returns:
            Duration in seconds.

        Raises:
            ValidationError: If the video file does not exist.
            PipelineError: If ffprobe fails.
        """
        if not video_path.exists():
            raise ValidationError(f"Video file not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            raise PipelineError(
                "ffprobe not found. Ensure FFmpeg is installed and on PATH."
            )
        except subprocess.TimeoutExpired:
            raise PipelineError(
                f"ffprobe timed out for {video_path}"
            )

        if result.returncode != 0:
            stderr_tail = result.stderr[-500:] if result.stderr else "(no stderr)"
            raise PipelineError(
                f"ffprobe failed (code {result.returncode}): {stderr_tail}"
            )

        try:
            probe_data = json.loads(result.stdout)
            duration = float(probe_data["format"]["duration"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            raise PipelineError(
                f"Failed to parse ffprobe output for {video_path}: {exc}"
            )

        logger.info("Video duration for %s: %.3f seconds", video_path, duration)
        return duration
