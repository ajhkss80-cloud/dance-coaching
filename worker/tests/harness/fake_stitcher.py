"""Fake video stitcher and frame interpolator for testing.

Provides controllable test doubles that record calls and produce
placeholder outputs for deterministic pipeline testing.
"""
from __future__ import annotations

from pathlib import Path

from src.application.ports.video_stitcher import FrameInterpolator, VideoStitcher


class FakeStitcher(VideoStitcher):
    """In-memory test double for VideoStitcher.

    Records all calls and produces placeholder output files.

    Attributes:
        concat_calls: List of (segment_paths, output_path, fps) tuples.
        mux_calls: List of (video_path, audio_path, output_path) tuples.
    """

    def __init__(self) -> None:
        self.concat_calls: list[tuple[list[Path], Path, int]] = []
        self.mux_calls: list[tuple[Path, Path, Path]] = []

    def concat_segments(
        self,
        segment_paths: list[Path],
        output_path: Path,
        fps: int = 30,
    ) -> Path:
        """Record the call and create a placeholder output file."""
        self.concat_calls.append((list(segment_paths), output_path, fps))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"FAKE_CONCAT_VIDEO")
        return output_path

    def mux_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        """Record the call and create a placeholder output file."""
        self.mux_calls.append((video_path, audio_path, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"FAKE_MUXED_VIDEO")
        return output_path


class FakeInterpolator(FrameInterpolator):
    """In-memory test double for FrameInterpolator.

    Records all calls and produces placeholder frame files.

    Attributes:
        initialize_calls: Number of times initialize was called.
        interpolate_calls: List of (seg_a, seg_b, num_frames) tuples.
        fail_on_boundary: If set, raises PipelineError for that boundary index.
    """

    def __init__(self, fail_on_boundary: int | None = None) -> None:
        self.initialize_calls: int = 0
        self.interpolate_calls: list[tuple[Path, Path, int]] = []
        self._fail_on_boundary = fail_on_boundary
        self._call_index = 0

    def initialize(self) -> None:
        """Record the initialization call."""
        self.initialize_calls += 1

    def interpolate_boundary(
        self,
        seg_a_path: Path,
        seg_b_path: Path,
        num_frames: int = 2,
    ) -> list[Path]:
        """Record the call and create placeholder frame files."""
        from src.domain.errors import PipelineError

        self.interpolate_calls.append((seg_a_path, seg_b_path, num_frames))

        if (
            self._fail_on_boundary is not None
            and self._call_index == self._fail_on_boundary
        ):
            self._call_index += 1
            raise PipelineError(
                f"Simulated interpolation failure at boundary {self._call_index - 1}"
            )

        self._call_index += 1

        # Create placeholder frame files
        output_dir = seg_a_path.parent / f"interp_{self._call_index - 1}"
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_paths: list[Path] = []
        for i in range(num_frames):
            frame_path = output_dir / f"frame_{i:04d}.png"
            frame_path.write_bytes(b"FAKE_FRAME_DATA")
            frame_paths.append(frame_path)
        return frame_paths
