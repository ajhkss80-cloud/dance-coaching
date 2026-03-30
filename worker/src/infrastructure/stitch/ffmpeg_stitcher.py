"""FFmpeg-based video stitching utilities.

Provides functions for splitting, concatenating, and muxing video
files using FFmpeg subprocess calls. All operations validate inputs
and raise PipelineError on failure.

Includes the ``FFmpegStitcher`` class that implements the
``VideoStitcher`` port for use in the orchestrator's stitch pipeline.
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from src.application.ports.video_stitcher import VideoStitcher
from src.domain.entities import Segment
from src.domain.errors import PipelineError, ValidationError

logger = logging.getLogger(__name__)


def _run_ffmpeg(cmd: list[str], description: str, timeout: int = 300) -> str:
    """Run an FFmpeg/ffprobe command with standard error handling.

    Args:
        cmd: Command and arguments to execute.
        description: Human-readable description for log messages.
        timeout: Maximum execution time in seconds.

    Returns:
        The stdout output from the command.

    Raises:
        PipelineError: If the command fails or times out.
    """
    logger.debug("Running: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        raise PipelineError(
            f"FFmpeg/ffprobe not found for '{description}'. "
            "Ensure FFmpeg is installed and on PATH."
        )
    except subprocess.TimeoutExpired:
        raise PipelineError(
            f"FFmpeg timed out during '{description}' "
            f"(timeout={timeout}s)"
        )

    if result.returncode != 0:
        stderr_tail = result.stderr[-500:] if result.stderr else "(no stderr)"
        raise PipelineError(
            f"FFmpeg '{description}' failed (code {result.returncode}): "
            f"{stderr_tail}"
        )

    return result.stdout


def get_video_info(path: Path) -> dict:
    """Get video metadata using ffprobe.

    Args:
        path: Path to the video file.

    Returns:
        Dictionary with keys: ``duration`` (float seconds),
        ``fps`` (float), ``width`` (int), ``height`` (int).

    Raises:
        ValidationError: If the file does not exist.
        PipelineError: If ffprobe fails.
    """
    if not path.exists():
        raise ValidationError(f"Video file not found: {path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]

    stdout = _run_ffmpeg(cmd, f"probe {path.name}", timeout=30)

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"Failed to parse ffprobe JSON: {exc}")

    # Extract duration (prefer format-level, fall back to stream-level)
    duration = 0.0
    if "format" in data and "duration" in data["format"]:
        duration = float(data["format"]["duration"])
    elif data.get("streams"):
        stream_dur = data["streams"][0].get("duration")
        if stream_dur:
            duration = float(stream_dur)

    # Extract resolution and frame rate from the first video stream
    width = 0
    height = 0
    fps = 0.0
    if data.get("streams"):
        stream = data["streams"][0]
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
        r_frame_rate = stream.get("r_frame_rate", "0/1")
        try:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    info = {
        "duration": duration,
        "fps": fps,
        "width": width,
        "height": height,
    }

    logger.info(
        "Video info for %s: %.2fs, %.1f fps, %dx%d",
        path.name, duration, fps, width, height,
    )

    return info


def split_video(
    input_path: Path,
    segments: list[Segment],
    output_dir: Path,
) -> list[Path]:
    """Split a video into segments at the specified boundaries.

    Uses FFmpeg stream copy (no re-encoding) for speed when possible.

    Args:
        input_path: Path to the source video.
        segments: List of Segment objects defining time boundaries.
        output_dir: Directory for output segment files.

    Returns:
        Ordered list of paths to the created segment files.

    Raises:
        ValidationError: If the input file does not exist.
        PipelineError: If any split operation fails.
    """
    if not input_path.exists():
        raise ValidationError(f"Input video not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []

    for segment in segments:
        output_path = output_dir / f"segment_{segment.index:04d}.mp4"
        duration = segment.end_time - segment.start_time

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{segment.start_time:.3f}",
            "-i", str(input_path),
            "-t", f"{duration:.3f}",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(output_path),
        ]

        _run_ffmpeg(
            cmd,
            f"split segment {segment.index} "
            f"({segment.start_time:.2f}-{segment.end_time:.2f}s)",
        )

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PipelineError(
                f"Split produced empty file for segment {segment.index}"
            )

        output_paths.append(output_path)
        logger.info(
            "Split segment %d: %.2f-%.2fs -> %s",
            segment.index, segment.start_time, segment.end_time,
            output_path.name,
        )

    return output_paths


def concat_videos(
    segment_paths: list[Path],
    output_path: Path,
    fps: int = 30,
) -> Path:
    """Concatenate multiple video segments into a single video.

    Uses the FFmpeg concat demuxer for lossless concatenation
    of segments that share the same codec and parameters.

    Args:
        segment_paths: Ordered list of segment video file paths.
        output_path: Path for the concatenated output file.
        fps: Output frame rate (used if re-encoding is needed).

    Returns:
        Path to the concatenated output file.

    Raises:
        PipelineError: If concatenation fails or no segments provided.
    """
    if not segment_paths:
        raise PipelineError("No segment paths provided for concatenation")

    for p in segment_paths:
        if not p.exists():
            raise PipelineError(f"Segment file not found: {p}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the concat demuxer file list
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        prefix="concat_list_",
    ) as f:
        for seg_path in segment_paths:
            # FFmpeg concat demuxer requires forward slashes or escaped paths
            safe_path = str(seg_path).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
        list_path = Path(f.name)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c", "copy",
            str(output_path),
        ]

        _run_ffmpeg(cmd, "concat segments")
    finally:
        list_path.unlink(missing_ok=True)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise PipelineError("Concatenation produced empty output file")

    logger.info(
        "Concatenated %d segments -> %s",
        len(segment_paths), output_path.name,
    )

    return output_path


def mux_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    """Combine a video file with an audio file.

    Replaces any existing audio in the video with the provided
    audio track.

    Args:
        video_path: Path to the video file (may have no audio).
        audio_path: Path to the audio file to mux in.
        output_path: Path for the combined output file.

    Returns:
        Path to the muxed output file.

    Raises:
        PipelineError: If muxing fails.
        ValidationError: If input files do not exist.
    """
    if not video_path.exists():
        raise ValidationError(f"Video file not found: {video_path}")
    if not audio_path.exists():
        raise ValidationError(f"Audio file not found: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]

    _run_ffmpeg(cmd, "mux audio")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise PipelineError("Audio muxing produced empty output file")

    logger.info(
        "Muxed audio: %s + %s -> %s",
        video_path.name, audio_path.name, output_path.name,
    )

    return output_path


class FFmpegStitcher(VideoStitcher):
    """VideoStitcher implementation using FFmpeg subprocess calls.

    Delegates to the module-level ``concat_videos`` and ``mux_audio``
    functions, providing a class-based interface that satisfies the
    ``VideoStitcher`` port for dependency injection.
    """

    def concat_segments(
        self,
        segment_paths: list[Path],
        output_path: Path,
        fps: int = 30,
    ) -> Path:
        """Concatenate video segments using the FFmpeg concat demuxer.

        Args:
            segment_paths: Ordered list of segment video file paths.
            output_path: Path for the concatenated output file.
            fps: Output frame rate (used if re-encoding is needed).

        Returns:
            Path to the concatenated output file.
        """
        return concat_videos(segment_paths, output_path, fps=fps)

    def mux_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        """Mux an audio track onto a video file.

        Args:
            video_path: Path to the video file.
            audio_path: Path to the audio file.
            output_path: Path for the combined output file.

        Returns:
            Path to the muxed output file.
        """
        return mux_audio(video_path, audio_path, output_path)
