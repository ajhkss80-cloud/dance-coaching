"""Fake generation backend for testing.

Provides a controllable test double that records calls and can simulate
failures on specific segments for error-handling tests.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from src.application.ports.generation_backend import GenerationBackend
from src.domain.errors import BackendError


class FakeBackend(GenerationBackend):
    """In-memory test double for GenerationBackend.

    Records all generate_segment calls and optionally fails on specified
    segment indices to test error handling paths.

    Attributes:
        delay: Simulated processing delay in seconds per segment.
        fail_on_segments: Set of segment indices that will raise BackendError.
        call_log: Ordered list of segment indices that were processed.
    """

    def __init__(
        self,
        delay: float = 0.01,
        fail_on_segments: list[int] | None = None,
    ) -> None:
        self.delay = delay
        self.fail_on_segments: list[int] = fail_on_segments or []
        self.call_log: list[int] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Mark the backend as initialized."""
        self._initialized = True

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Simulate segment generation with optional failure injection.

        Args:
            avatar_path: Path to the avatar image.
            segment_path: Path to the reference segment.
            segment_index: Index of the segment being generated.
            options: Backend-specific options (ignored in fake).

        Returns:
            Path to a placeholder output file.

        Raises:
            BackendError: If segment_index is in fail_on_segments.
        """
        self.call_log.append(segment_index)

        if segment_index in self.fail_on_segments:
            raise BackendError(f"Simulated failure at segment {segment_index}")

        await asyncio.sleep(self.delay)

        # Create a placeholder video file
        output_path = segment_path.parent / f"generated_{segment_index}.mp4"
        output_path.write_bytes(b"FAKE_VIDEO_DATA")
        return output_path

    async def cleanup(self) -> None:
        """Mark the backend as no longer initialized."""
        self._initialized = False

    def name(self) -> str:
        """Return the backend name."""
        return "fake"

    @property
    def initialized(self) -> bool:
        """Whether the backend has been initialized."""
        return self._initialized
