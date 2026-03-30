"""Integration tests for the full generation pipeline.

Tests the orchestrator with fake backend and audio processor
combined with real or fake stitcher/interpolator to verify
end-to-end pipeline behaviour including progress reporting
and error handling.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.application.orchestrator import GenerationOrchestrator
from src.domain.entities import GenerateJob
from src.domain.errors import BackendError
from tests.harness.fake_audio_processor import FakeAudioProcessor
from tests.harness.fake_backend import FakeBackend
from tests.harness.fake_stitcher import FakeInterpolator, FakeStitcher


def _make_job(tmp_path: Path, job_id: str = "integ-001") -> GenerateJob:
    """Create a GenerateJob with real temporary files."""
    avatar = tmp_path / "avatar.png"
    avatar.write_bytes(b"PNG_DATA_FOR_TEST")
    reference = tmp_path / "reference.mp4"
    reference.write_bytes(b"MP4_DATA_FOR_TEST")
    return GenerateJob(
        job_id=job_id,
        avatar_path=avatar,
        reference_path=reference,
        backend_type="cloud",
    )


class TestFullPipelineWithFakeBackend:
    """End-to-end pipeline tests using FakeBackend + FakeStitcher."""

    @pytest.mark.asyncio
    async def test_full_pipeline_produces_output(self, tmp_path: Path) -> None:
        """Full pipeline with all fakes produces a final output file."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 3.0, 5.0, 7.0, 9.0, 11.0],
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
            job=job,
            progress_callback=progress_values.append,
            skip_stitch=False,
        )

        # Output exists
        assert result.exists()
        assert result.stat().st_size > 0

        # All segments were generated
        assert len(backend.call_log) > 0
        assert len(job.segments) > 0

        # Stitcher was invoked
        assert len(stitcher.concat_calls) == 1
        assert len(stitcher.mux_calls) == 1

        # Concat received the correct number of paths (segments + interp frames)
        concat_input = stitcher.concat_calls[0][0]
        num_segments = len(job.segments)
        num_boundaries = max(0, num_segments - 1)
        # Each boundary produces 2 interp frames
        expected_paths = num_segments + (num_boundaries * 2)
        assert len(concat_input) == expected_paths

    @pytest.mark.asyncio
    async def test_full_pipeline_skip_stitch(self, tmp_path: Path) -> None:
        """Pipeline with skip_stitch=True returns segments dir."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0],
            duration=8.0,
        )

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
        )

        result = await orchestrator.run(
            job=job,
            progress_callback=lambda _: None,
            skip_stitch=True,
        )

        assert result.is_dir()
        assert result.name == "generated"

    @pytest.mark.asyncio
    async def test_full_pipeline_single_segment(self, tmp_path: Path) -> None:
        """Pipeline handles a single-segment video correctly."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 2.0],
            duration=3.0,
        )
        stitcher = FakeStitcher()
        interpolator = FakeInterpolator()

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=stitcher,
            interpolator=interpolator,
        )

        result = await orchestrator.run(
            job=job,
            progress_callback=lambda _: None,
            skip_stitch=False,
        )

        assert result.exists()
        # Single segment means no interpolation boundaries
        assert len(interpolator.interpolate_calls) == 0
        # But concat and mux still happen
        assert len(stitcher.concat_calls) == 1
        assert len(stitcher.mux_calls) == 1


class TestPipelineProgressCallback:
    """Tests verifying progress update behaviour through the pipeline."""

    @pytest.mark.asyncio
    async def test_progress_callback_called_correctly(
        self, tmp_path: Path
    ) -> None:
        """Progress callback receives monotonically increasing values 0-100."""
        job = _make_job(tmp_path)
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

        await orchestrator.run(
            job=job,
            progress_callback=progress_values.append,
            skip_stitch=False,
        )

        # All values are in valid range
        for v in progress_values:
            assert 0.0 <= v <= 100.0

        # Monotonically increasing
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

        # Starts with validation (5%) and ends at 100%
        assert progress_values[0] == 5.0
        assert progress_values[-1] == 100.0

        # Key milestones present
        assert 10.0 in progress_values  # audio extraction
        assert 20.0 in progress_values  # beat detection
        assert 25.0 in progress_values  # segmentation
        assert 30.0 in progress_values  # video split
        assert 90.0 in progress_values  # interpolation
        assert 95.0 in progress_values  # concat
        assert 98.0 in progress_values  # mux

    @pytest.mark.asyncio
    async def test_progress_reaches_100_on_skip_stitch(
        self, tmp_path: Path
    ) -> None:
        """Progress reaches 100% even with skip_stitch=True."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001)
        audio_proc = FakeAudioProcessor(duration=5.0)

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
        )

        progress_values: list[float] = []

        await orchestrator.run(
            job=job,
            progress_callback=progress_values.append,
            skip_stitch=True,
        )

        assert progress_values[-1] == 100.0


class TestPipelineHandlesBackendFailure:
    """Tests for error handling when the backend fails."""

    @pytest.mark.asyncio
    async def test_backend_failure_propagates(self, tmp_path: Path) -> None:
        """Backend failure on a segment propagates as BackendError."""
        job = _make_job(tmp_path)
        # Fail on the third segment (index 2)
        backend = FakeBackend(delay=0.001, fail_on_segments=[2])
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0, 15.0, 20.0],
            duration=25.0,
        )
        stitcher = FakeStitcher()
        interpolator = FakeInterpolator()

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=stitcher,
            interpolator=interpolator,
        )

        with pytest.raises(BackendError, match="Simulated failure at segment 2"):
            await orchestrator.run(
                job=job,
                progress_callback=lambda _: None,
                skip_stitch=False,
            )

        # Backend cleanup should still have been called (via finally block)
        assert not backend.initialized

    @pytest.mark.asyncio
    async def test_backend_failure_on_first_segment(
        self, tmp_path: Path
    ) -> None:
        """Backend failure on the first segment is handled correctly."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001, fail_on_segments=[0])
        audio_proc = FakeAudioProcessor(duration=5.0)

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
            stitcher=FakeStitcher(),
        )

        with pytest.raises(BackendError, match="segment 0"):
            await orchestrator.run(
                job=job,
                progress_callback=lambda _: None,
                skip_stitch=False,
            )

    @pytest.mark.asyncio
    async def test_backend_failure_cleans_up(self, tmp_path: Path) -> None:
        """Backend cleanup is called even when generation fails."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001, fail_on_segments=[1])
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0],
            duration=12.0,
        )

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
        )

        with pytest.raises(BackendError):
            await orchestrator.run(
                job=job,
                progress_callback=lambda _: None,
                skip_stitch=True,
            )

        # Backend was initialized then cleaned up despite failure
        assert backend.initialized is False

    @pytest.mark.asyncio
    async def test_progress_stops_at_failure_point(
        self, tmp_path: Path
    ) -> None:
        """Progress callback stops receiving updates after failure."""
        job = _make_job(tmp_path)
        backend = FakeBackend(delay=0.001, fail_on_segments=[1])
        audio_proc = FakeAudioProcessor(
            beat_times=[1.0, 5.0, 10.0],
            duration=12.0,
        )

        orchestrator = GenerationOrchestrator(
            backend=backend,
            audio_processor=audio_proc,
        )

        progress_values: list[float] = []

        with pytest.raises(BackendError):
            await orchestrator.run(
                job=job,
                progress_callback=progress_values.append,
                skip_stitch=True,
            )

        # Progress should NOT reach 100
        assert progress_values[-1] < 100.0
        # But should have some progress from completed steps
        assert len(progress_values) > 0
