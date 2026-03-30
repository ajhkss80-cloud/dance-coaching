"""Port (interface) for video generation backends.

Defines the contract that any generation backend must fulfill,
whether cloud-based (Kling API) or local (GPU-based model).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GenerationBackend(ABC):
    """Abstract base class for dance video generation backends.

    Implementations are responsible for generating a single video segment
    from an avatar image and a reference choreography segment.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the backend, loading models or establishing connections.

        Raises:
            BackendError: If initialization fails.
        """
        ...

    @abstractmethod
    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Generate a video segment from an avatar and reference segment.

        Args:
            avatar_path: Path to the avatar image file.
            segment_path: Path to the reference video segment.
            segment_index: Zero-based index of the segment being generated.
            options: Backend-specific generation options.

        Returns:
            Path to the generated video segment file.

        Raises:
            BackendError: If generation fails.
            InsufficientResourceError: If resources (GPU memory, etc.) are exhausted.
        """
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Release resources held by the backend.

        Should be called when the backend is no longer needed.
        Must be safe to call multiple times.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the human-readable name of this backend.

        Returns:
            A string identifying the backend implementation.
        """
        ...
