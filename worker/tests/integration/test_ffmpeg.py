"""Integration tests for FFmpeg stitcher utilities.

Tests require FFmpeg to be installed and available on PATH.
Automatically skipped when FFmpeg is not found.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from src.domain.entities import Segment
from src.domain.errors import PipelineError, ValidationError

# Skip the entire module if ffmpeg is not installed
_ffmpeg_available = shutil.which("ffmpeg") is not None
pytestmark = pytest.mark.skipif(
    not _ffmpeg_available,
    reason="FFmpeg not installed",
)


def _create_test_video(path: Path, duration: float = 3.0, fps: int = 30) -> Path:
    """Create a minimal test video using the sample_data helper."""
    from tests.harness.sample_data import create_sample_video
    return create_sample_video(path, duration=duration, fps=fps)


def _create_test_audio(path: Path, duration: float = 3.0) -> Path:
    """Create a minimal test audio file using the sample_data helper."""
    from tests.harness.sample_data import create_sample_audio
    return create_sample_audio(path, duration=duration)


class TestGetVideoInfo:
    """Tests for the get_video_info function."""

    def test_get_video_info_returns_duration(self, tmp_path: Path) -> None:
        """Video info contains a positive duration."""
        from src.infrastructure.stitch.ffmpeg_stitcher import get_video_info

        video = _create_test_video(tmp_path / "sample.mp4", duration=3.0)
        info = get_video_info(video)

        assert info["duration"] > 0
        assert info["duration"] == pytest.approx(3.0, abs=0.5)

    def test_get_video_info_returns_fps(self, tmp_path: Path) -> None:
        """Video info contains a reasonable frame rate."""
        from src.infrastructure.stitch.ffmpeg_stitcher import get_video_info

        video = _create_test_video(tmp_path / "sample.mp4", fps=30)
        info = get_video_info(video)

        assert info["fps"] > 0
        assert info["fps"] == pytest.approx(30.0, abs=2.0)

    def test_get_video_info_returns_resolution(self, tmp_path: Path) -> None:
        """Video info contains non-zero width and height."""
        from src.infrastructure.stitch.ffmpeg_stitcher import get_video_info

        video = _create_test_video(tmp_path / "sample.mp4")
        info = get_video_info(video)

        assert info["width"] > 0
        assert info["height"] > 0

    def test_get_video_info_missing_file(self, tmp_path: Path) -> None:
        """Raises ValidationError for a non-existent file."""
        from src.infrastructure.stitch.ffmpeg_stitcher import get_video_info

        with pytest.raises(ValidationError, match="not found"):
            get_video_info(tmp_path / "nonexistent.mp4")


class TestSplitVideo:
    """Tests for the split_video function."""

    def test_split_video_produces_segments(self, tmp_path: Path) -> None:
        """Splitting a 6-second video at 3 seconds produces 2 files."""
        from src.infrastructure.stitch.ffmpeg_stitcher import split_video

        video = _create_test_video(tmp_path / "source.mp4", duration=6.0)
        out_dir = tmp_path / "segments"

        segments = [
            Segment(index=0, start_time=0.0, end_time=3.0),
            Segment(index=1, start_time=3.0, end_time=6.0),
        ]

        paths = split_video(video, segments, out_dir)

        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            assert p.stat().st_size > 0

    def test_split_video_segment_naming(self, tmp_path: Path) -> None:
        """Output files follow the segment_XXXX.mp4 naming convention."""
        from src.infrastructure.stitch.ffmpeg_stitcher import split_video

        video = _create_test_video(tmp_path / "source.mp4", duration=4.0)
        out_dir = tmp_path / "segments"

        segments = [
            Segment(index=0, start_time=0.0, end_time=2.0),
            Segment(index=1, start_time=2.0, end_time=4.0),
        ]

        paths = split_video(video, segments, out_dir)

        assert paths[0].name == "segment_0000.mp4"
        assert paths[1].name == "segment_0001.mp4"

    def test_split_video_missing_input(self, tmp_path: Path) -> None:
        """Raises ValidationError when input video does not exist."""
        from src.infrastructure.stitch.ffmpeg_stitcher import split_video

        segments = [Segment(index=0, start_time=0.0, end_time=3.0)]

        with pytest.raises(ValidationError, match="not found"):
            split_video(tmp_path / "missing.mp4", segments, tmp_path / "out")


class TestConcatVideos:
    """Tests for the concat_videos function."""

    def test_concat_two_segments(self, tmp_path: Path) -> None:
        """Concatenating two segments produces a valid output file."""
        from src.infrastructure.stitch.ffmpeg_stitcher import (
            concat_videos,
            get_video_info,
            split_video,
        )

        video = _create_test_video(tmp_path / "source.mp4", duration=6.0)
        seg_dir = tmp_path / "segments"

        segments = [
            Segment(index=0, start_time=0.0, end_time=3.0),
            Segment(index=1, start_time=3.0, end_time=6.0),
        ]

        seg_paths = split_video(video, segments, seg_dir)
        output = tmp_path / "combined.mp4"

        result = concat_videos(seg_paths, output)

        assert result.exists()
        assert result.stat().st_size > 0

        info = get_video_info(result)
        # Combined duration should be approximately the sum
        assert info["duration"] > 0

    def test_concat_empty_list(self) -> None:
        """Raises PipelineError when given an empty segment list."""
        from src.infrastructure.stitch.ffmpeg_stitcher import concat_videos

        with pytest.raises(PipelineError, match="No segment"):
            concat_videos([], Path("output.mp4"))


class TestMuxAudio:
    """Tests for the mux_audio function."""

    def test_mux_audio_produces_output(self, tmp_path: Path) -> None:
        """Muxing video and audio produces a non-empty output file."""
        from src.infrastructure.stitch.ffmpeg_stitcher import mux_audio

        video = _create_test_video(tmp_path / "video.mp4", duration=3.0)
        audio = _create_test_audio(tmp_path / "audio.wav", duration=3.0)
        output = tmp_path / "muxed.mp4"

        result = mux_audio(video, audio, output)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_mux_audio_missing_video(self, tmp_path: Path) -> None:
        """Raises ValidationError when video file is missing."""
        from src.infrastructure.stitch.ffmpeg_stitcher import mux_audio

        audio = _create_test_audio(tmp_path / "audio.wav")

        with pytest.raises(ValidationError, match="not found"):
            mux_audio(
                tmp_path / "missing.mp4",
                audio,
                tmp_path / "output.mp4",
            )

    def test_mux_audio_missing_audio(self, tmp_path: Path) -> None:
        """Raises ValidationError when audio file is missing."""
        from src.infrastructure.stitch.ffmpeg_stitcher import mux_audio

        video = _create_test_video(tmp_path / "video.mp4")

        with pytest.raises(ValidationError, match="not found"):
            mux_audio(
                video,
                tmp_path / "missing.wav",
                tmp_path / "output.mp4",
            )
