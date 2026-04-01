"""WaveSpeed AI cloud backend for video generation.

Implements the GenerationBackend ABC using the WaveSpeed AI API,
supporting both SteadyDancer and Wan 2.2 Animate Move models.
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

# Model path mapping
_MODEL_PATHS: dict[str, str] = {
    "steady-dancer": "wavespeed-ai/steady-dancer",
    "wan-animate": "wavespeed-ai/wan-2.2/animate",
}

# Pricing per second of output (USD)
_PRICING: dict[str, dict[str, float]] = {
    "steady-dancer": {"480p": 0.04, "720p": 0.08},
    "wan-animate": {"480p": 0.04, "720p": 0.08},
}

# Polling constants
_POLL_INTERVAL_SEC = 5.0
_POLL_TIMEOUT_SEC = 600.0
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SEC = 2.0


class WaveSpeedBackend(GenerationBackend):
    """Cloud-based video generation backend using the WaveSpeed AI API.

    Supports two models:
    - SteadyDancer: High-quality dance motion transfer
    - Wan 2.2 Animate Move: General-purpose motion transfer

    Attributes:
        api_key: WaveSpeed AI API authentication key.
        model: Model identifier ("steady-dancer" or "wan-animate").
        resolution: Output resolution ("480p" or "720p").
        base_url: Base URL for the WaveSpeed AI API.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "steady-dancer",
        resolution: str = "720p",
        base_url: str = "https://api.wavespeed.ai",
    ) -> None:
        if not api_key:
            raise BackendError("WaveSpeed API key must not be empty")
        if model not in _MODEL_PATHS:
            raise BackendError(
                f"Unknown WaveSpeed model '{model}'. "
                f"Must be one of: {list(_MODEL_PATHS.keys())}"
            )
        if resolution not in ("480p", "720p"):
            raise BackendError(
                f"Resolution must be '480p' or '720p', got '{resolution}'"
            )

        self._api_key = api_key
        self._model = model
        self._model_path = _MODEL_PATHS[model]
        self._resolution = resolution
        self._base_url = base_url.rstrip("/")
        self._client = None
        self._total_cost = 0.0

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
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, read=120.0),
        )

        # Test connectivity
        try:
            response = await self._client.get(
                f"{self._base_url}/api/v3/health"
            )
            if response.status_code >= 500:
                raise BackendError(
                    f"WaveSpeed API health check returned {response.status_code}"
                )
        except BackendError:
            raise
        except Exception as exc:
            logger.warning(
                "WaveSpeed API health check failed (non-fatal): %s", exc
            )

        self._total_cost = 0.0
        logger.info(
            "WaveSpeed backend initialized (model=%s, resolution=%s)",
            self._model,
            self._resolution,
        )

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Generate a video segment via the WaveSpeed AI API.

        Reads the avatar image and reference segment, submits them
        to the appropriate model endpoint, polls for completion,
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
            "Generating segment %d via WaveSpeed (%s)",
            segment_index,
            self._model,
        )

        # Encode inputs as base64 data URIs
        avatar_b64 = base64.b64encode(avatar_path.read_bytes()).decode("ascii")
        segment_b64 = base64.b64encode(
            segment_path.read_bytes()
        ).decode("ascii")

        # Determine MIME types
        avatar_suffix = avatar_path.suffix.lower()
        avatar_mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(avatar_suffix, "image/png")

        avatar_data_uri = f"data:{avatar_mime};base64,{avatar_b64}"
        video_data_uri = f"data:video/mp4;base64,{segment_b64}"

        # Submit generation request
        request_id = await self._submit_request(
            avatar_data_uri, video_data_uri, segment_index
        )

        # Poll for completion
        result_url = await self._poll_result(request_id, segment_index)

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
            logger.info(
                "WaveSpeed backend closed (total estimated cost: $%.4f)",
                self._total_cost,
            )

    def name(self) -> str:
        """Return the backend name including the model variant."""
        return f"wavespeed-{self._model}"

    async def _submit_request(
        self,
        image_data: str,
        video_data: str,
        segment_index: int,
    ) -> str:
        """Submit a generation request to the WaveSpeed API.

        Args:
            image_data: Base64 data URI for the avatar image.
            video_data: Base64 data URI for the reference video.
            segment_index: Segment index for logging.

        Returns:
            The request ID for polling.

        Raises:
            BackendError: After exhausting retries.
        """
        url = f"{self._base_url}/api/v3/{self._model_path}"
        payload = {
            "image": image_data,
            "video": video_data,
            "resolution": self._resolution,
        }

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post(url, json=payload)

                if response.status_code == 429:
                    backoff = _INITIAL_BACKOFF_SEC * (2**attempt)
                    logger.warning(
                        "WaveSpeed API rate limited (429) on segment %d, "
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
                        f"WaveSpeed API submission failed for segment "
                        f"{segment_index} (status {response.status_code}): "
                        f"{response.text[:200]}"
                    )

                data = response.json()
                request_id = data.get("requestId")
                if not request_id:
                    raise BackendError(
                        f"WaveSpeed API returned no requestId for segment "
                        f"{segment_index}: {data}"
                    )

                logger.info(
                    "Submitted segment %d, requestId=%s",
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
                    "WaveSpeed API request error on segment %d (attempt %d): %s",
                    segment_index,
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(backoff)

        raise BackendError(
            f"Failed to submit segment {segment_index} after "
            f"{_MAX_RETRIES} retries: {last_error}"
        )

    async def _poll_result(
        self, request_id: str, segment_index: int
    ) -> str:
        """Poll the WaveSpeed API until the request completes.

        Args:
            request_id: The request ID from submission.
            segment_index: Segment index for logging.

        Returns:
            The download URL for the generated video.

        Raises:
            BackendError: On task failure or timeout.
        """
        url = (
            f"{self._base_url}/api/v3/predictions/{request_id}/result"
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

                if status == "completed":
                    output = data.get("output", {})
                    video_url = None

                    # Handle various response shapes
                    if isinstance(output, str):
                        video_url = output
                    elif isinstance(output, dict):
                        video_url = output.get("video_url") or output.get(
                            "url"
                        )
                    elif isinstance(output, list) and output:
                        video_url = output[0]

                    if not video_url:
                        raise BackendError(
                            f"Request {request_id} completed but no video URL "
                            f"found in output: {data}"
                        )

                    # Log cost estimate
                    duration = data.get("duration", 0)
                    if duration:
                        try:
                            duration_val = float(duration)
                        except (TypeError, ValueError):
                            duration_val = 0.0
                        cost_per_sec = _PRICING.get(
                            self._model, {}
                        ).get(self._resolution, 0.08)
                        cost = duration_val * cost_per_sec
                        self._total_cost += cost
                        logger.info(
                            "Segment %d cost estimate: $%.4f (%.1fs @ $%.2f/s)",
                            segment_index,
                            cost,
                            duration_val,
                            cost_per_sec,
                        )

                    return video_url

                if status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    raise BackendError(
                        f"WaveSpeed request {request_id} failed for segment "
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
            f"WaveSpeed request {request_id} timed out after "
            f"{_POLL_TIMEOUT_SEC}s for segment {segment_index}"
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
                        prefix=f"wavespeed_seg{segment_index}_",
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
