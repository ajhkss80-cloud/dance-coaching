"""Unit tests for the Kling API backend.

Tests mock httpx to verify correct API request format, polling
logic, retry behaviour, and timeout handling without requiring
a live Kling API connection.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.errors import BackendError
from src.infrastructure.backends.kling_backend import (
    KlingBackend,
    _AVATAR_MAX_BYTES,
    _VIDEO_MAX_BYTES,
)


class TestKlingRequestFormat:
    """Tests verifying the correct Kling API request body format."""

    @pytest.mark.asyncio
    async def test_kling_request_uses_image2video_endpoint(
        self, tmp_path: Path
    ) -> None:
        """Submit task posts to /v1/videos/image2video with correct body."""
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG_DATA")
        segment = tmp_path / "segment.mp4"
        segment.write_bytes(b"MP4_DATA")

        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task_id": "task-123", "status": "processing"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock()

        # Mock health check response
        health_response = MagicMock()
        health_response.status_code = 200
        mock_client.get.return_value = health_response

        backend._client = mock_client

        import base64
        avatar_b64 = base64.b64encode(b"PNG_DATA").decode("ascii")
        segment_b64 = base64.b64encode(b"MP4_DATA").decode("ascii")

        task_id = await backend._submit_task(avatar_b64, segment_b64, 0)

        assert task_id == "task-123"

        # Verify the post was called with correct endpoint and payload
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/v1/videos/image2video"

        payload = call_args[1]["json"]
        assert payload["model_name"] == "kling-v3"
        assert payload["mode"] == "pro"
        assert payload["image"] == avatar_b64
        assert payload["video"] == segment_b64
        assert payload["duration"] == "10"
        assert payload["cfg_scale"] == 0.5
        assert payload["motion_control"]["type"] == "reference_video"

    @pytest.mark.asyncio
    async def test_kling_request_validates_avatar_size(
        self, tmp_path: Path
    ) -> None:
        """Avatar files exceeding 10MB are rejected before API call."""
        avatar = tmp_path / "avatar_large.png"
        avatar.write_bytes(b"x" * (_AVATAR_MAX_BYTES + 1))
        segment = tmp_path / "segment.mp4"
        segment.write_bytes(b"MP4_DATA")

        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")
        backend._client = AsyncMock()

        with pytest.raises(BackendError, match="Avatar file too large"):
            await backend.generate_segment(avatar, segment, 0, {})

    @pytest.mark.asyncio
    async def test_kling_request_validates_segment_size(
        self, tmp_path: Path
    ) -> None:
        """Segment files exceeding 100MB are rejected before API call."""
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG_DATA")
        segment = tmp_path / "segment_large.mp4"
        segment.write_bytes(b"x" * (_VIDEO_MAX_BYTES + 1))

        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")
        backend._client = AsyncMock()

        with pytest.raises(BackendError, match="Segment video too large"):
            await backend.generate_segment(avatar, segment, 0, {})


class TestKlingPollingLogic:
    """Tests for the task polling state machine."""

    @pytest.mark.asyncio
    async def test_kling_polling_completed(self) -> None:
        """Polling returns video_url when task status is completed."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "task_id": "task-123",
            "status": "completed",
            "video_url": "https://cdn.kling.test/result.mp4",
            "duration": 10,
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=completed_response)
        backend._client = mock_client

        url = await backend._poll_task("task-123", 0)
        assert url == "https://cdn.kling.test/result.mp4"

    @pytest.mark.asyncio
    async def test_kling_polling_processing_then_completed(self) -> None:
        """Polling handles processing status before completion."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        processing_response = MagicMock()
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "task_id": "task-123",
            "status": "processing",
        }

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "task_id": "task-123",
            "status": "completed",
            "video_url": "https://cdn.kling.test/result.mp4",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[processing_response, completed_response]
        )
        backend._client = mock_client

        # Patch sleep to avoid actual wait
        with patch("src.infrastructure.backends.kling_backend.asyncio.sleep", new_callable=AsyncMock):
            url = await backend._poll_task("task-123", 0)

        assert url == "https://cdn.kling.test/result.mp4"
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_kling_polling_failed_task(self) -> None:
        """Polling raises BackendError when task status is failed."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        failed_response = MagicMock()
        failed_response.status_code = 200
        failed_response.json.return_value = {
            "task_id": "task-123",
            "status": "failed",
            "error": "Model inference error",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=failed_response)
        backend._client = mock_client

        with pytest.raises(BackendError, match="failed"):
            await backend._poll_task("task-123", 0)

    @pytest.mark.asyncio
    async def test_kling_polling_uses_correct_endpoint(self) -> None:
        """Polling GET requests use /v1/videos/image2video/{task_id}."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "task_id": "task-abc",
            "status": "completed",
            "video_url": "https://cdn.kling.test/result.mp4",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=completed_response)
        backend._client = mock_client

        await backend._poll_task("task-abc", 0)

        mock_client.get.assert_called_once_with("/v1/videos/image2video/task-abc")


class TestKlingRetryLogic:
    """Tests for retry behaviour on rate limiting."""

    @pytest.mark.asyncio
    async def test_kling_retry_on_429(self) -> None:
        """429 response triggers retry with exponential backoff."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"task_id": "task-123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[rate_limited, success])
        backend._client = mock_client

        with patch("src.infrastructure.backends.kling_backend.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            task_id = await backend._submit_task("img_b64", "vid_b64", 0)

        assert task_id == "task-123"
        assert mock_client.post.call_count == 2
        # First retry should have a backoff
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_kling_exhausts_retries_on_429(self) -> None:
        """Exhausting retries on 429 raises BackendError."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        rate_limited = MagicMock()
        rate_limited.status_code = 429

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=rate_limited)
        backend._client = mock_client

        with patch("src.infrastructure.backends.kling_backend.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(BackendError, match="retries"):
                await backend._submit_task("img_b64", "vid_b64", 0)


class TestKlingTimeout:
    """Tests for task timeout behaviour."""

    @pytest.mark.asyncio
    async def test_kling_timeout_raises_backend_error(self) -> None:
        """Polling timeout raises BackendError after exceeding limit."""
        backend = KlingBackend(api_key="test-key", base_url="https://api.kling.test")

        # Always return processing status
        processing_response = MagicMock()
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "task_id": "task-forever",
            "status": "processing",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=processing_response)
        backend._client = mock_client

        # Patch both sleep and the timeout to speed up test
        with patch(
            "src.infrastructure.backends.kling_backend._POLL_TIMEOUT_SEC", 10.0
        ), patch(
            "src.infrastructure.backends.kling_backend._POLL_INTERVAL_SEC", 5.0
        ), patch(
            "src.infrastructure.backends.kling_backend.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(BackendError, match="timed out"):
                await backend._poll_task("task-forever", 0)


class TestKlingConstruction:
    """Tests for KlingBackend construction."""

    def test_empty_api_key_raises(self) -> None:
        """Empty API key raises BackendError at construction."""
        with pytest.raises(BackendError, match="must not be empty"):
            KlingBackend(api_key="", base_url="https://api.kling.test")

    def test_name(self) -> None:
        """Backend reports correct name."""
        backend = KlingBackend(api_key="key", base_url="https://api.kling.test")
        assert backend.name() == "kling-cloud"

    @pytest.mark.asyncio
    async def test_generate_without_initialize_raises(
        self, tmp_path: Path
    ) -> None:
        """Calling generate_segment before initialize raises BackendError."""
        backend = KlingBackend(api_key="key", base_url="https://api.kling.test")
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG")
        segment = tmp_path / "seg.mp4"
        segment.write_bytes(b"MP4")

        with pytest.raises(BackendError, match="not initialised"):
            await backend.generate_segment(avatar, segment, 0, {})

    @pytest.mark.asyncio
    async def test_cleanup_safe_when_not_initialized(self) -> None:
        """Cleanup is safe to call without initialization."""
        backend = KlingBackend(api_key="key", base_url="https://api.kling.test")
        await backend.cleanup()  # Should not raise
