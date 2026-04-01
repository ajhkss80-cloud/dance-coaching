"""fal.ai cloud backend for video generation.

Implements the GenerationBackend ABC using the fal.ai queue API,
supporting Kling V3 Motion Control and Wan 2.2 Animate Move models.
Handles submission, polling, download, and retry logic.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import tempfile
from pathlib import Path

from src.application.ports.generation_backend import GenerationBackend
from src.domain.errors import BackendError

logger = logging.getLogger(__name__)

# Model ID mapping
_MODEL_IDS: dict[str, str] = {
    "kling-v3-standard-mc": "fal-ai/kling-video/v3/standard/motion-control",
    "kling-v3-pro-mc": "fal-ai/kling-video/v3/pro/motion-control",
    "wan-animate": "fal-ai/wan/v2.2-14b/animate/move",
}

# Polling constants
_POLL_INTERVAL_SEC = 5.0
_POLL_TIMEOUT_SEC = 600.0
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SEC = 2.0


class FalAIBackend(GenerationBackend):
    """Cloud-based video generation backend using the fal.ai queue API.

    Supports three models:
    - Kling V3 Standard MC: Cost-effective motion control
    - Kling V3 Pro MC: High-quality motion control
    - Wan 2.2 Animate Move: General-purpose motion transfer

    Attributes:
        api_key: fal.ai API authentication key.
        model: Model identifier mapped to fal.ai model IDs.
        character_orientation: Orientation mode ("video" or "image").
    """

    def __init__(
        self,
        api_key: str,
        model: str = "kling-v3-standard-mc",
        character_orientation: str = "video",
    ) -> None:
        if not api_key:
            raise BackendError("fal.ai API key must not be empty")
        if model not in _MODEL_IDS:
            raise BackendError(
                f"Unknown fal.ai model '{model}'. "
                f"Must be one of: {list(_MODEL_IDS.keys())}"
            )
        if character_orientation not in ("video", "image"):
            raise BackendError(
                f"character_orientation must be 'video' or 'image', "
                f"got '{character_orientation}'"
            )

        self._api_key = api_key
        self._model = model
        self._model_id = _MODEL_IDS[model]
        self._character_orientation = character_orientation
        self._base_url = "https://queue.fal.run"
        self._client = None

    async def initialize(self) -> None:
        """Initialize the HTTP client and verify API connectivity.

        Raises:
            BackendError: If the API is unreachable or the key is invalid.
        """
        try:
            import httpx
        except ImportError:
            raise BackendError(
                "httpx is not installed. Install with: pip install httpx"
            )

        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Key {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, read=120.0),
        )

        logger.info(
            "fal.ai backend initialized (model=%s, orientation=%s)",
            self._model,
            self._character_orientation,
        )

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Generate a video segment via the fal.ai queue API.

        Encodes the avatar image and reference segment as base64 data URIs,
        submits them to the model endpoint, polls for completion,
        and downloads the result.

        Args:
            avatar_path: Path to the avatar image file.
            segment_path: Path to the reference video segment.
            segment_index: Zero-based index of this segment.
            options: Backend-specific generation options.

        Returns:
            Path to the downloaded generated video file.

        Raises:
            BackendError: On API errors, timeouts, or download failures.
        """
        if self._client is None:
            raise BackendError(
                "Backend not initialized. Call initialize() first."
            )

        logger.info(
            "Generating segment %d via fal.ai (%s)",
            segment_index,
            self._model,
        )

        # Encode inputs as base64 data URIs
        avatar_b64 = base64.b64encode(avatar_path.read_bytes()).decode("ascii")
        segment_b64 = base64.b64encode(
            segment_path.read_bytes()
        ).decode("ascii")

        avatar_suffix = avatar_path.suffix.lower()
        avatar_mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(avatar_suffix, "image/png")

        image_url = f"data:{avatar_mime};base64,{avatar_b64}"
        video_url = f"data:video/mp4;base64,{segment_b64}"

        # Submit generation request
        request_id = await self._submit_request(
            image_url, video_url, segment_index
        )

        # Poll for completion
        await self._poll_status(request_id, segment_index)

        # Get result
        result_url = await self._get_result(request_id, segment_index)

        # Download result
        output_path = await self._download_result(
            result_url, segment_index
        )

        logger.info(
            "Segment %d generation complete: %s",
            segment_index,
            output_path,
        )
        return output_path

    async def cleanup(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("fal.ai backend closed")

    def name(self) -> str:
        """Return the backend name including the model variant."""
        return f"falai-{self._model}"

    async def _submit_request(
        self,
        image_url: str,
        video_url: str,
        segment_index: int,
    ) -> str:
        """Submit a generation request to the fal.ai queue.

        Args:
            image_url: Data URI for the avatar image.
            video_url: Data URI for the reference video.
            segment_index: Segment index for logging.

        Returns:
            The request ID for polling.

        Raises:
            BackendError: After exhausting retries.
        """
        url = f"{self._base_url}/{self._model_id}"
        payload = {
            "image_url": image_url,
            "video_url": video_url,
            "character_orientation": self._character_orientation,
        }

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post(url, json=payload)

                if response.status_code == 429:
                    backoff = _INITIAL_BACKOFF_SEC * (2**attempt)
                    logger.warning(
                        "fal.ai API rate limited (429) on segment %d, "
                        "retry %d/%d in %.1fs",
                        segment_index,
                        attempt + 1,
                        _MAX_RETRIES,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code >= 400:
                    raise BackendError(
                        f"fal.ai API submission failed for segment "
                        f"{segment_index} (status {response.status_code}): "
                        f"{response.text[:200]}"
                    )

                data = response.json()
                request_id = data.get("request_id")
                if not request_id:
                    raise BackendError(
                        f"fal.ai API returned no request_id for segment "
                        f"{segment_index}: {data}"
                    )

                logger.info(
                    "Submitted segment %d, request_id=%s",
                    segment_index,
                    request_id,
                )
                return request_id

            except BackendError:
                raise
            except Exception as exc:
                last_error = exc
                backoff = _INITIAL_BACKOFF_SEC * (2**attempt)
                logger.warning(
                    "fal.ai API request error on segment %d (attempt %d): %s",
                    segment_index,
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(backoff)

        raise BackendError(
            f"Failed to submit segment {segment_index} after "
            f"{_MAX_RETRIES} retries: {last_error}"
        )

    async def _poll_status(
        self, request_id: str, segment_index: int
    ) -> None:
        """Poll the fal.ai queue until the request completes.

        Args:
            request_id: The request ID from submission.
            segment_index: Segment index for logging.

        Raises:
            BackendError: On task failure or timeout.
        """
        url = (
            f"{self._base_url}/{self._model_id}"
            f"/requests/{request_id}/status"
        )
        elapsed = 0.0

        while elapsed < _POLL_TIMEOUT_SEC:
            try:
                response = await self._client.get(url)

                if response.status_code >= 400:
                    raise BackendError(
                        f"Status check failed for {request_id} "
                        f"(status {response.status_code})"
                    )

                data = response.json()
                status = data.get("status", "unknown")

                if status == "COMPLETED":
                    logger.info(
                        "Segment %d request %s completed",
                        segment_index,
                        request_id,
                    )
                    return

                if status == "FAILED":
                    error_msg = data.get("error", "Unknown error")
                    raise BackendError(
                        f"fal.ai request {request_id} failed for segment "
                        f"{segment_index}: {error_msg}"
                    )

                logger.debug(
                    "Segment %d request %s status: %s (%.0fs elapsed)",
                    segment_index,
                    request_id,
                    status,
                    elapsed,
                )

            except BackendError:
                raise
            except Exception as exc:
                logger.warning(
                    "Error polling request %s: %s", request_id, exc
                )

            await asyncio.sleep(_POLL_INTERVAL_SEC)
            elapsed += _POLL_INTERVAL_SEC

        raise BackendError(
            f"fal.ai request {request_id} timed out after "
            f"{_POLL_TIMEOUT_SEC}s for segment {segment_index}"
        )

    async def _get_result(
        self, request_id: str, segment_index: int
    ) -> str:
        """Retrieve the result of a completed fal.ai request.

        Args:
            request_id: The request ID.
            segment_index: Segment index for logging.

        Returns:
            The download URL for the generated video.

        Raises:
            BackendError: If result retrieval fails.
        """
        url = (
            f"{self._base_url}/{self._model_id}"
            f"/requests/{request_id}"
        )

        try:
            response = await self._client.get(url)

            if response.status_code >= 400:
                raise BackendError(
                    f"Result retrieval failed for {request_id} "
                    f"(status {response.status_code})"
                )

            data = response.json()

            # fal.ai returns video URL in various nested structures
            video_url = None
            video_data = data.get("video", {})
            if isinstance(video_data, dict):
                video_url = video_data.get("url")
            elif isinstance(video_data, str):
                video_url = video_data

            if not video_url:
                # Try alternative response shapes
                video_url = data.get("video_url") or data.get("output_url")

            if not video_url:
                raise BackendError(
                    f"Request {request_id} completed but no video URL "
                    f"found: {data}"
                )

            return video_url

        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(
                f"Error retrieving result for {request_id}: {exc}"
            )

    async def _download_result(
        self, url: str, segment_index: int
    ) -> Path:
        """Download the generated video from the given URL.

        Args:
            url: Download URL for the generated video.
            segment_index: Segment index for file naming.

        Returns:
            Path to the downloaded file.

        Raises:
            BackendError: If the download fails.
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as dl_client:
                response = await dl_client.get(url)
                if response.status_code != 200:
                    raise BackendError(
                        f"Download failed for segment {segment_index} "
                        f"(status {response.status_code})"
                    )

                output_path = Path(
                    tempfile.mktemp(
                        suffix=".mp4",
                        prefix=f"falai_seg{segment_index}_",
                    )
                )
                output_path.write_bytes(response.content)

                logger.info(
                    "Downloaded segment %d: %s (%.1f KB)",
                    segment_index,
                    output_path,
                    len(response.content) / 1024,
                )
                return output_path

        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(
                f"Download error for segment {segment_index}: {exc}"
            )
