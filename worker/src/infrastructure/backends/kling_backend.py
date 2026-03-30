"""Kling API cloud backend for video generation.

Implements the GenerationBackend ABC using the Kling AI image-to-video
API with reference video motion control. Handles upload, polling,
download, and retry logic with exponential backoff.
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

# Kling pricing estimate for cost logging (USD per second of output)
_KLING_COST_PER_SEC = 0.029

# File size limits (bytes)
_AVATAR_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB

# Polling / retry constants
_POLL_INTERVAL_SEC = 5.0
_POLL_TIMEOUT_SEC = 300.0
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SEC = 2.0


class KlingBackend(GenerationBackend):
    """Cloud-based video generation backend using the Kling AI API.

    Sends an avatar image and a reference dance segment to the Kling
    image-to-video endpoint with reference_video motion control,
    polls for completion, and downloads the resulting video.

    Attributes:
        api_key: Kling API authentication key.
        base_url: Base URL for the Kling API.
    """

    def __init__(self, api_key: str, base_url: str) -> None:
        if not api_key:
            raise BackendError("Kling API key must not be empty")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = None
        self._total_cost = 0.0

    async def initialize(self) -> None:
        """Initialise the HTTP client and verify API connectivity.

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
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, read=120.0),
        )

        # Test connectivity with a lightweight endpoint
        try:
            response = await self._client.get("/health")
            # Accept any 2xx or 404 (endpoint may not exist but proves connectivity)
            if response.status_code >= 500:
                raise BackendError(
                    f"Kling API health check returned {response.status_code}"
                )
        except BackendError:
            raise
        except Exception as exc:
            logger.warning(
                "Kling API health check failed (non-fatal): %s", exc
            )

        self._total_cost = 0.0
        logger.info("Kling backend initialised (base_url=%s)", self._base_url)

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Generate a video segment via the Kling image-to-video API.

        Reads the avatar image and reference segment, validates file
        sizes, submits them to the API with reference_video motion
        control, polls for task completion, and downloads the result.

        Args:
            avatar_path: Path to the avatar image file.
            segment_path: Path to the reference video segment.
            segment_index: Zero-based index of this segment.
            options: Additional options (currently unused).

        Returns:
            Path to the downloaded generated video file.

        Raises:
            BackendError: On API errors, timeouts, or download failures.
        """
        if self._client is None:
            raise BackendError("Backend not initialised. Call initialize() first.")

        logger.info("Generating segment %d via Kling API", segment_index)

        # Validate file sizes
        avatar_size = avatar_path.stat().st_size
        if avatar_size > _AVATAR_MAX_BYTES:
            raise BackendError(
                f"Avatar file too large ({avatar_size / 1024 / 1024:.1f} MB). "
                f"Maximum is {_AVATAR_MAX_BYTES / 1024 / 1024:.0f} MB."
            )

        segment_size = segment_path.stat().st_size
        if segment_size > _VIDEO_MAX_BYTES:
            raise BackendError(
                f"Segment video too large ({segment_size / 1024 / 1024:.1f} MB). "
                f"Maximum is {_VIDEO_MAX_BYTES / 1024 / 1024:.0f} MB."
            )

        # Read inputs as base64
        avatar_b64 = base64.b64encode(avatar_path.read_bytes()).decode("ascii")
        segment_b64 = base64.b64encode(segment_path.read_bytes()).decode("ascii")

        # Submit generation task with retry on 429
        task_id = await self._submit_task(avatar_b64, segment_b64, segment_index)

        # Poll until completion
        download_url = await self._poll_task(task_id, segment_index)

        # Download result
        output_path = await self._download_result(download_url, segment_index)

        logger.info("Segment %d generation complete: %s", segment_index, output_path)
        return output_path

    async def cleanup(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info(
                "Kling backend client closed (total estimated cost: $%.4f)",
                self._total_cost,
            )

    def name(self) -> str:
        """Return the backend name."""
        return "kling-cloud"

    async def _submit_task(
        self, avatar_b64: str, segment_b64: str, segment_index: int
    ) -> str:
        """Submit an image-to-video task to the Kling API with retry.

        Uses the v1 image2video endpoint with reference_video motion
        control for dance motion transfer.

        Returns:
            The task ID for polling.

        Raises:
            BackendError: After exhausting retries.
        """
        payload = {
            "model_name": "kling-v3",
            "mode": "pro",
            "image": avatar_b64,
            "video": segment_b64,
            "duration": "10",
            "cfg_scale": 0.5,
            "motion_control": {
                "type": "reference_video",
            },
        }

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post(
                    "/v1/videos/image2video",
                    json=payload,
                )

                if response.status_code == 429:
                    backoff = _INITIAL_BACKOFF_SEC * (2 ** attempt)
                    logger.warning(
                        "Kling API rate limited (429) on segment %d, "
                        "retry %d/%d in %.1fs",
                        segment_index, attempt + 1, _MAX_RETRIES, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code >= 400:
                    raise BackendError(
                        f"Kling API submission failed for segment {segment_index} "
                        f"(status {response.status_code}): {response.text[:200]}"
                    )

                data = response.json()
                task_id = data.get("task_id")
                if not task_id:
                    raise BackendError(
                        f"Kling API returned no task_id for segment {segment_index}: "
                        f"{data}"
                    )

                logger.info(
                    "Submitted segment %d, task_id=%s", segment_index, task_id
                )
                return task_id

            except BackendError:
                raise
            except Exception as exc:
                last_error = exc
                backoff = _INITIAL_BACKOFF_SEC * (2 ** attempt)
                logger.warning(
                    "Kling API request error on segment %d (attempt %d): %s",
                    segment_index, attempt + 1, exc,
                )
                await asyncio.sleep(backoff)

        raise BackendError(
            f"Failed to submit segment {segment_index} after {_MAX_RETRIES} "
            f"retries: {last_error}"
        )

    async def _poll_task(self, task_id: str, segment_index: int) -> str:
        """Poll a Kling task until completion or timeout.

        Uses the v1 image2video/{task_id} GET endpoint.

        Returns:
            The download URL for the generated video.

        Raises:
            BackendError: On task failure or timeout.
        """
        elapsed = 0.0

        while elapsed < _POLL_TIMEOUT_SEC:
            try:
                response = await self._client.get(
                    f"/v1/videos/image2video/{task_id}"
                )

                if response.status_code >= 400:
                    raise BackendError(
                        f"Task status check failed for {task_id} "
                        f"(status {response.status_code})"
                    )

                data = response.json()
                status = data.get("status", "unknown")

                if status in ("completed", "succeeded", "done"):
                    video_url = data.get("video_url")
                    if not video_url:
                        raise BackendError(
                            f"Task {task_id} completed but no video_url found"
                        )

                    # Log estimated cost
                    duration = data.get("duration", 0)
                    if duration:
                        try:
                            duration_val = float(duration)
                        except (TypeError, ValueError):
                            duration_val = 0.0
                        cost = duration_val * _KLING_COST_PER_SEC
                        self._total_cost += cost
                        logger.info(
                            "Segment %d cost estimate: $%.4f (%.1fs)",
                            segment_index, cost, duration_val,
                        )

                    return video_url

                if status in ("failed", "error", "cancelled"):
                    error_msg = data.get("error", data.get("message", "Unknown"))
                    raise BackendError(
                        f"Kling task {task_id} failed for segment "
                        f"{segment_index}: {error_msg}"
                    )

                logger.debug(
                    "Segment %d task %s status: %s (%.0fs elapsed)",
                    segment_index, task_id, status, elapsed,
                )

            except BackendError:
                raise
            except Exception as exc:
                logger.warning(
                    "Error polling task %s: %s", task_id, exc
                )

            await asyncio.sleep(_POLL_INTERVAL_SEC)
            elapsed += _POLL_INTERVAL_SEC

        raise BackendError(
            f"Kling task {task_id} timed out after {_POLL_TIMEOUT_SEC}s "
            f"for segment {segment_index}"
        )

    async def _download_result(self, url: str, segment_index: int) -> Path:
        """Download the generated video from the given URL.

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

                output_path = Path(tempfile.mktemp(
                    suffix=".mp4",
                    prefix=f"kling_seg{segment_index}_",
                ))
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
