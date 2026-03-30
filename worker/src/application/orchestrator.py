"""Generation orchestrator coordinating the video generation pipeline.

Manages the end-to-end flow of generating a dance tutorial video:
audio extraction, beat detection, segmentation, per-segment generation,
interpolation, concatenation, and audio muxing.
"""
from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

from src.application.ports.audio_processor import AudioProcessor
from src.application.ports.generation_backend import GenerationBackend
from src.application.ports.video_stitcher import FrameInterpolator, VideoStitcher
from src.domain.entities import GenerateJob, Segment
from src.domain.errors import PipelineError, ValidationError

logger = logging.getLogger(__name__)

# Maximum duration of a single generation segment in seconds
SEGMENT_MAX_LENGTH_SEC = 10.0


class GenerationOrchestrator:
    """Orchestrates the complete video generation pipeline.

    Coordinates between the generation backend, audio processor,
    video stitcher, and frame interpolator to produce a dance
    tutorial video from an avatar image and reference choreography.
    """

    def __init__(
        self,
        backend: GenerationBackend,
        audio_processor: AudioProcessor,
        stitcher: VideoStitcher | None = None,
        interpolator: FrameInterpolator | None = None,
    ) -> None:
        self._backend = backend
        self._audio_processor = audio_processor
        self._stitcher = stitcher
        self._interpolator = interpolator

    async def run(
        self,
        job: GenerateJob,
        progress_callback: Callable[[float], None],
        skip_stitch: bool = False,
    ) -> Path:
        """Execute the full generation pipeline.

        Args:
            job: The generation job containing input paths and configuration.
            progress_callback: Called with progress percentage (0-100).
            skip_stitch: If True, skip stitch steps (interpolation,
                concat, audio mux) and return the directory of generated segments.

        Returns:
            Path to the final output video, or the segments directory
            if skip_stitch is True.

        Raises:
            ValidationError: If input files are missing or invalid.
            PipelineError: If any pipeline step fails.
            BackendError: If the generation backend encounters an error.
        """
        work_dir = Path(tempfile.mkdtemp(prefix=f"dance_gen_{job.job_id}_"))
        segments_dir = work_dir / "segments"
        segments_dir.mkdir(exist_ok=True)
        generated_dir = work_dir / "generated"
        generated_dir.mkdir(exist_ok=True)

        # Step 1 (5%): Validate inputs exist
        self._validate_inputs(job)
        progress_callback(5.0)
        logger.info("Step 1/10: Input validation complete for job %s", job.job_id)

        # Step 2 (10%): Extract audio
        audio_path = work_dir / "audio.wav"
        self._audio_processor.extract_audio(job.reference_path, audio_path)
        progress_callback(10.0)
        logger.info("Step 2/10: Audio extraction complete")

        # Step 3 (20%): Detect beats
        beat_times = self._audio_processor.detect_beats(audio_path)
        progress_callback(20.0)
        logger.info("Step 3/10: Beat detection complete, found %d beats", len(beat_times))

        # Step 4 (25%): Calculate segment boundaries
        total_duration = self._audio_processor.get_duration(job.reference_path)
        segments = self._calculate_segments(
            beat_times=beat_times,
            max_segment_sec=SEGMENT_MAX_LENGTH_SEC,
            total_duration=total_duration,
        )
        job.segments = segments
        progress_callback(25.0)
        logger.info(
            "Step 4/10: Segmentation complete, %d segments calculated",
            len(segments),
        )

        # Step 5 (30%): Split reference video into segments
        segment_paths = self._split_reference_video(
            reference_path=job.reference_path,
            segments=segments,
            output_dir=segments_dir,
        )
        progress_callback(30.0)
        logger.info("Step 5/10: Reference video split into %d segments", len(segment_paths))

        # Step 6 (30-85%): Generate each segment via backend
        await self._backend.initialize()
        generated_paths: list[Path] = []
        try:
            for i, (segment, segment_path) in enumerate(zip(segments, segment_paths)):
                segment_progress = 30.0 + (55.0 * (i + 1) / len(segments))
                result_path = await self._backend.generate_segment(
                    avatar_path=job.avatar_path,
                    segment_path=segment_path,
                    segment_index=segment.index,
                    options={},
                )
                generated_paths.append(result_path)
                progress_callback(min(segment_progress, 85.0))
                logger.info(
                    "Step 6/10: Segment %d/%d generated",
                    i + 1,
                    len(segments),
                )
        finally:
            await self._backend.cleanup()

        if skip_stitch:
            progress_callback(100.0)
            logger.info("Skipping stitch steps (skip_stitch=True)")
            return generated_dir

        # Verify stitch dependencies are available
        if self._stitcher is None:
            raise PipelineError(
                "VideoStitcher is required for stitch steps but was not provided. "
                "Inject a VideoStitcher or set skip_stitch=True."
            )

        # Step 7 (90%): RIFE interpolation to smooth boundaries
        interpolated_paths = self._interpolate_segments(generated_paths)
        progress_callback(90.0)
        logger.info("Step 7/10: Interpolation complete")

        # Step 8 (95%): FFmpeg concat all segments into one video
        concat_path = work_dir / "concat.mp4"
        self._stitcher.concat_segments(interpolated_paths, concat_path)
        progress_callback(95.0)
        logger.info("Step 8/10: Concatenation complete")

        # Step 9 (98%): Mux the extracted audio back onto the stitched video
        output_path = work_dir / "output_final.mp4"
        self._stitcher.mux_audio(concat_path, audio_path, output_path)
        progress_callback(98.0)
        logger.info("Step 9/10: Audio muxing complete")

        # Step 10 (100%): Done
        progress_callback(100.0)
        logger.info("Step 10/10: Generation pipeline complete for job %s", job.job_id)

        return output_path

    def _validate_inputs(self, job: GenerateJob) -> None:
        """Validate that all required input files exist.

        Raises:
            ValidationError: If any input file is missing.
        """
        if not job.avatar_path.exists():
            raise ValidationError(
                f"Avatar file not found: {job.avatar_path}"
            )
        if not job.reference_path.exists():
            raise ValidationError(
                f"Reference video not found: {job.reference_path}"
            )

    def _calculate_segments(
        self,
        beat_times: list[float],
        max_segment_sec: float,
        total_duration: float,
    ) -> list[Segment]:
        """Calculate segment boundaries aligned to beats.

        Groups consecutive beats into segments that do not exceed
        max_segment_sec in duration. If no beats are detected,
        creates uniform segments of max_segment_sec length.

        Args:
            beat_times: Sorted list of beat timestamps in seconds.
            max_segment_sec: Maximum allowed segment duration.
            total_duration: Total video duration in seconds.

        Returns:
            A list of Segment value objects covering the full duration.
        """
        if total_duration <= 0:
            raise ValidationError(
                f"Total duration must be positive, got {total_duration}"
            )

        # Handle case with no beats or very few beats
        if len(beat_times) < 2:
            return self._uniform_segments(max_segment_sec, total_duration)

        segments: list[Segment] = []
        segment_start = 0.0
        segment_index = 0

        for beat_time in beat_times:
            if beat_time <= segment_start:
                continue

            # Check if adding this beat would exceed the max length
            if beat_time - segment_start >= max_segment_sec:
                # Close the current segment at this beat
                segments.append(
                    Segment(
                        index=segment_index,
                        start_time=segment_start,
                        end_time=beat_time,
                    )
                )
                segment_start = beat_time
                segment_index += 1

        # Close the final segment to cover remaining duration
        if segment_start < total_duration:
            segments.append(
                Segment(
                    index=segment_index,
                    start_time=segment_start,
                    end_time=total_duration,
                )
            )

        # Safety: if beat grouping produced no segments, fall back to uniform
        if not segments:
            return self._uniform_segments(max_segment_sec, total_duration)

        return segments

    def _uniform_segments(
        self, max_segment_sec: float, total_duration: float
    ) -> list[Segment]:
        """Create uniform segments when beat data is unavailable."""
        segments: list[Segment] = []
        start = 0.0
        index = 0
        while start < total_duration:
            end = min(start + max_segment_sec, total_duration)
            segments.append(Segment(index=index, start_time=start, end_time=end))
            start = end
            index += 1
        return segments

    def _split_reference_video(
        self,
        reference_path: Path,
        segments: list[Segment],
        output_dir: Path,
    ) -> list[Path]:
        """Split the reference video into segment files.

        In the current phase, this creates placeholder segment files.
        Full FFmpeg-based splitting will be implemented in Phase 3
        infrastructure layer.

        Returns:
            List of paths to segment video files.
        """
        segment_paths: list[Path] = []
        for segment in segments:
            segment_path = output_dir / f"segment_{segment.index:04d}.mp4"
            # Write segment metadata as placeholder content
            # Infrastructure layer will replace with actual FFmpeg splitting
            segment_path.write_text(
                f"segment:{segment.index},"
                f"start:{segment.start_time:.3f},"
                f"end:{segment.end_time:.3f},"
                f"source:{reference_path}"
            )
            segment_paths.append(segment_path)
        return segment_paths

    def _interpolate_segments(self, segment_paths: list[Path]) -> list[Path]:
        """Apply frame interpolation to smooth boundaries between segments.

        If an interpolator is available, generates intermediate frames
        between adjacent segments and inserts them into the ordered list.
        If no interpolator is available, returns the paths unchanged.

        Args:
            segment_paths: Ordered list of generated segment video paths.

        Returns:
            Ordered list of paths including any interpolation frame videos.
        """
        if self._interpolator is None or len(segment_paths) < 2:
            return list(segment_paths)

        self._interpolator.initialize()

        result: list[Path] = []
        for i, seg_path in enumerate(segment_paths):
            result.append(seg_path)
            if i < len(segment_paths) - 1:
                try:
                    interp_frames = self._interpolator.interpolate_boundary(
                        seg_a_path=seg_path,
                        seg_b_path=segment_paths[i + 1],
                        num_frames=2,
                    )
                    result.extend(interp_frames)
                except PipelineError:
                    logger.warning(
                        "Interpolation failed between segments %d and %d; "
                        "skipping boundary smoothing",
                        i, i + 1,
                    )

        return result
