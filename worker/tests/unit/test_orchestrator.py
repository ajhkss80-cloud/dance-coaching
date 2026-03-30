"""Unit tests for the GenerationOrchestrator."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.application.orchestrator import GenerationOrchestrator, SEGMENT_MAX_LENGTH_SEC
from src.domain.entities import GenerateJob
from src.domain.errors import PipelineError
from tests.harness.fake_audio_processor import FakeAudioProcessor
from tests.harness.fake_backend import FakeBackend
from tests.harness.fake_stitcher import FakeInterpolator, FakeStitcher


class TestCalculateSegments:
    """Tests for the _calculate_segments method."""

    @pytest.fixture()
    def orchestrator(self) -> GenerationOrchestrator:
        """Create an orchestrator with fake dependencies."""
        backend = FakeBackend()
        audio_processor = FakeAudioProcessor()
        return GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_processor,
        )

    def test_calculate_segments_basic(
        self, orchestrator: GenerationOrchestrator
    ) -> None:
        """Ten beats over 15 seconds with max 10s segments produces expected segments."""
        beat_times = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
        total_duration = 15.0
        max_seg = 10.0

        segments = orchestrator._calculate_segments(
            beat_times=beat_times,
            max_segment_sec=max_seg,
            total_duration=total_duration,
        )

        # All segments must have valid boundaries
        assert len(segments) >= 1
        assert segments[0].start_time == 0.0
        assert segments[-1].end_time == total_duration

        # No segment exceeds max length (with small float tolerance)
        for seg in segments:
            assert seg.duration <= max_seg + 0.001, (
                f"Segment {seg.index} duration {seg.duration:.3f} exceeds max {max_seg}"
            )

        # Segments are contiguous (no gaps)
        for i in range(1, len(segments)):
            assert segments[i].start_time == pytest.approx(
                segments[i - 1].end_time
            ), f"Gap between segments {i-1} and {i}"

        # Indices are sequential
        for i, seg in enumerate(segments):
            assert seg.index == i

    def test_calculate_segments_single_segment(
        self, orchestrator: GenerationOrchestrator
    ) -> None:
        """A short video should produce a single segment."""
        beat_times = [0.5, 1.0, 1.5, 2.0]
        total_duration = 3.0
        max_seg = 10.0

        segments = orchestrator._calculate_segments(
            beat_times=beat_times,
            max_segment_sec=max_seg,
            total_duration=total_duration,
        )

        # Short video should produce exactly one segment
        assert len(segments) == 1
        assert segments[0].start_time == 0.0
        assert segments[0].end_time == total_duration
        assert segments[0].duration == pytest.approx(3.0)

    def test_calculate_segments_respects_max_length(
        self, orchestrator: GenerationOrchestrator
    ) -> None:
        """No segment exceeds the maximum length."""
        # Dense beats over a long duration
        beat_times = [float(i) * 0.5 for i in range(120)]  # 60 seconds of beats
        total_duration = 60.0
        max_seg = 5.0

        segments = orchestrator._calculate_segments(
            beat_times=beat_times,
            max_segment_sec=max_seg,
            total_duration=total_duration,
        )

        for seg in segments:
            assert seg.duration <= max_seg + 0.001, (
                f"Segment {seg.index} duration {seg.duration:.3f} exceeds max {max_seg}"
            )

        # Coverage: first segment starts at 0, last ends at total_duration
        assert segments[0].start_time == 0.0
        assert segments[-1].end_time == pytest.approx(total_duration)

    def test_calculate_segments_no_beats(
        self, orchestrator: GenerationOrchestrator
    ) -> None:
        """With no beats, uniform segments are created."""
        segments = orchestrator._calculate_segments(
            beat_times=[],
            max_segment_sec=10.0,
            total_duration=25.0,
        )

        # Should create uniform segments
        assert len(segments) == 3  # 10 + 10 + 5
        assert segments[0].duration == pytest.approx(10.0)
        assert segments[1].duration == pytest.approx(10.0)
        assert segments[2].duration == pytest.approx(5.0)

    def test_calculate_segments_one_beat(
        self, orchestrator: GenerationOrchestrator
    ) -> None:
        """With only one beat, falls back to uniform segments."""
        segments = orchestrator._calculate_segments(
            beat_times=[5.0],
            max_segment_sec=10.0,
            total_duration=20.0,
        )

        # Fewer than 2 beats -> uniform fallback
        assert len(segments) == 2
        assert segments[0].duration == pytest.approx(10.0)
        assert segments[1].duration == pytest.approx(10.0)

    def test_calculate_segments_rejects_zero_duration(
        self, orchestrator: GenerationOrchestrator
    ) -> None:
        """Zero duration raises ValidationError."""
        from src.domain.errors import ValidationError

        with pytest.raises(ValidationError, match="positive"):
            orchestrator._calculate_segments(
                beat_times=[1.0, 2.0],
                max_segment_sec=10.0,
                total_duration=0.0,
            )


class TestOrchestratorRun:
    """Tests for the full orchestrator run method."""

    @pytest.fixture()
    def tmp_job(self, tmp_path: Path) -> GenerateJob:
        """Create a GenerateJob with real temporary files."""
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG_DATA")
        reference = tmp_path / "reference.mp4"
        reference.write_bytes(b"MP4_DATA")

        return GenerateJob(
            job_id="test-run-001",
            avatar_path=avatar,
            reference_path=reference,
            backend_type="cloud",
        )

    @pytest.mark.asyncio
    async def test_run_skip_stitch(self, tmp_job: GenerateJob) -> None:
        """Orchestrator completes successfully with skip_stitch=True."""
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 2.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0],
            duration=15.0,
        )
        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
        )

        progress_values: list[float] = []

        result = await orchestrator.run(
            job=tmp_job,
            progress_callback=progress_values.append,
            skip_stitch=True,
        )

        # Result should be a valid path
        assert isinstance(result, Path)

        # Progress should monotonically increase to 100
        assert progress_values[-1] == 100.0
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

        # Backend should have been called for each segment
        assert len(backend.call_log) > 0

    @pytest.mark.asyncio
    async def test_run_without_stitch_deps_raises_pipeline_error(
        self, tmp_job: GenerateJob
    ) -> None:
        """Running without stitcher raises PipelineError when skip_stitch=False."""
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0],
            duration=12.0,
        )
        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
        )

        with pytest.raises(PipelineError, match="VideoStitcher is required"):
            await orchestrator.run(
                job=tmp_job,
                progress_callback=lambda _: None,
                skip_stitch=False,
            )

    @pytest.mark.asyncio
    async def test_run_with_stitcher_completes(self, tmp_job: GenerateJob) -> None:
        """Orchestrator completes the full pipeline when stitcher is provided."""
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0],
            duration=12.0,
        )
        stitcher = FakeStitcher()
        interpolator = FakeInterpolator()

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=stitcher,
            interpolator=interpolator,
        )

        progress_values: list[float] = []

        result = await orchestrator.run(
            job=tmp_job,
            progress_callback=progress_values.append,
            skip_stitch=False,
        )

        # Result should be a file path ending in output_final.mp4
        assert isinstance(result, Path)
        assert result.name == "output_final.mp4"
        assert result.exists()

        # Progress should reach 100
        assert progress_values[-1] == 100.0

        # Stitcher should have been called
        assert len(stitcher.concat_calls) == 1
        assert len(stitcher.mux_calls) == 1

        # Interpolator should have been initialized and called for boundaries
        assert interpolator.initialize_calls == 1
        # With N segments, there are N-1 boundaries
        num_segments = len(tmp_job.segments)
        if num_segments > 1:
            assert len(interpolator.interpolate_calls) == num_segments - 1

    @pytest.mark.asyncio
    async def test_run_with_stitcher_no_interpolator(
        self, tmp_job: GenerateJob
    ) -> None:
        """Pipeline completes without interpolator (graceful degradation)."""
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0],
            duration=12.0,
        )
        stitcher = FakeStitcher()

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=stitcher,
            interpolator=None,
        )

        progress_values: list[float] = []

        result = await orchestrator.run(
            job=tmp_job,
            progress_callback=progress_values.append,
            skip_stitch=False,
        )

        assert isinstance(result, Path)
        assert result.exists()
        assert progress_values[-1] == 100.0

        # Stitcher still called even without interpolator
        assert len(stitcher.concat_calls) == 1
        assert len(stitcher.mux_calls) == 1

    @pytest.mark.asyncio
    async def test_run_interpolator_failure_is_nonfatal(
        self, tmp_job: GenerateJob
    ) -> None:
        """Pipeline completes even if interpolation fails at a boundary."""
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0],
            duration=12.0,
        )
        stitcher = FakeStitcher()
        # Fail on the first boundary interpolation
        interpolator = FakeInterpolator(fail_on_boundary=0)

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=stitcher,
            interpolator=interpolator,
        )

        result = await orchestrator.run(
            job=tmp_job,
            progress_callback=lambda _: None,
            skip_stitch=False,
        )

        # Should complete despite interpolation failure
        assert isinstance(result, Path)
        assert result.exists()

    @pytest.mark.asyncio
    async def test_run_progress_monotonic_with_stitch(
        self, tmp_job: GenerateJob
    ) -> None:
        """Progress is monotonically increasing through stitch steps."""
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0],
            duration=8.0,
        )
        stitcher = FakeStitcher()
        interpolator = FakeInterpolator()

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=stitcher,
            interpolator=interpolator,
        )

        progress_values: list[float] = []

        await orchestrator.run(
            job=tmp_job,
            progress_callback=progress_values.append,
            skip_stitch=False,
        )

        # Progress values: 5, 10, 20, 25, 30, ..., 85, 90, 95, 98, 100
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1], (
                f"Progress decreased from {progress_values[i-1]} to {progress_values[i]}"
            )

        # Must include stitch milestones
        assert 90.0 in progress_values
        assert 95.0 in progress_values
        assert 98.0 in progress_values
        assert 100.0 in progress_values
