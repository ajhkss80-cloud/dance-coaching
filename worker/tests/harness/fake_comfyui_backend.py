"""Fake ComfyUI backend for testing without a running ComfyUI server.

Simulates the ComfyUI API interaction with configurable behavior
for testing the generation pipeline.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from src.application.ports.generation_backend import GenerationBackend
from src.domain.errors import BackendError


class FakeComfyUIBackend(GenerationBackend):
    """Test double for ComfyUIBackend.

    Simulates ComfyUI API behavior without requiring a running server.
    Records all calls for assertion in tests.

    Args:
        delay: Simulated generation delay per segment (seconds).
        fail_on_segments: List of segment indices that should fail.
        model_name: Simulated model name.
    """

    def __init__(
        self,
        delay: float = 0.01,
        fail_on_segments: list[int] | None = None,
        model_name: str = "SteadyDancerBasic",
    ) -> None:
        self.delay = delay
        self.fail_on_segments = fail_on_segments or []
        self.model_name = model_name
        self.call_log: list[dict] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Simulate connecting to ComfyUI server."""
        self._initialized = True

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Simulate generating a segment via ComfyUI.

        Records the call and creates a placeholder output file.
        """
        if not self._initialized:
            raise BackendError("Backend not initialized")

        self.call_log.append(
            {
                "segment_index": segment_index,
                "avatar_path": str(avatar_path),
                "segment_path": str(segment_path),
                "options": options,
            }
        )

        if segment_index in self.fail_on_segments:
            raise BackendError(
                f"Simulated ComfyUI failure at segment {segment_index}"
            )

        await asyncio.sleep(self.delay)

        output_path = segment_path.parent / f"comfyui_seg{segment_index}.mp4"
        output_path.write_bytes(b"FAKE_COMFYUI_VIDEO")
        return output_path

    async def cleanup(self) -> None:
        """Simulate cleanup."""
        self._initialized = False

    def name(self) -> str:
        """Return the simulated backend name."""
        return f"comfyui-{self.model_name}"
