"""Unit tests for the Kling (EvoLink) API backend.

Tests mock httpx to verify correct EvoLink API request format,
polling logic, retry behaviour, and timeout handling without
requiring a live API connection.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.errors import BackendError
from src.infrastructure.backends.kling_backend import (
    KlingBackend,
    _AVATAR_MAX_BYTES,
    _VIDEO_MAX_BYTES,
)


class TestKlingConstruction:
    """Tests for KlingBackend construction."""

    def test_empty_api_key_raises(self) -> None:
        """Empty API key raises BackendError at construction."""
        with pytest.raises(BackendError, match="must not be empty"):
            KlingBackend(api_key="")

    def test_name(self) -> None:
        """Backend reports correct name."""
        backend = KlingBackend(api_key="key")
        assert backend.name() == "kling-evolink"

    def test_default_quality(self) -> None:
        """Default quality is 720p."""
        backend = KlingBackend(api_key="key")
        assert backend._quality == "720p"

    def test_custom_quality_1080p(self) -> None:
        """Custom quality 1080p is accepted."""
        backend = KlingBackend(api_key="key", quality="1080p")
        assert backend._quality == "1080p"

    def test_invalid_quality_raises(self) -> None:
        """Invalid quality raises BackendError."""
        with pytest.raises(BackendError, match="Quality must be"):
            KlingBackend(api_key="key", quality="4k")

    def test_character_orientation_video(self) -> None:
        """Video orientation is accepted."""
        backend = KlingBackend(
            api_key="key", character_orientation="video"
        )
        assert backend._character_orientation == "video"

    def test_character_orientation_image(self) -> None:
        """Image orientation is accepted."""
        backend = KlingBackend(
            api_key="key", character_orientation="image"
        )
        assert backend._character_orientation == "image"

    def test_invalid_orientation_raises(self) -> None:
        """Invalid character_orientation raises BackendError."""
        with pytest.raises(BackendError, match="character_orientation"):
            KlingBackend(api_key="key", character_orientation="auto")

    @pytest.mark.asyncio
    async def test_generate_without_initialize_raises(
        self, tmp_path: Path
    ) -> None:
        """Calling generate_segment before initialize raises BackendError."""
        backend = KlingBackend(api_key="key")
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG")
        segment = tmp_path / "seg.mp4"
        segment.write_bytes(b"MP4")

        with pytest.raises(BackendError, match="not initialized"):
            await backend.generate_segment(avatar, segment, 0, {})

    @pytest.mark.asyncio
    async def test_cleanup_safe_when_not_initialized(self) -> None:
        """Cleanup is safe to call without initialization."""
        backend = KlingBackend(api_key="key")
        await backend.cleanup()  # Should not raise


class TestEvoLinkRequestFormat:
    """Tests verifying the correct EvoLink API request body format."""

    @pytest.mark.asyncio
    async def test_evolink_request_format(self) -> None:
        """Submit task posts to /videos/generations with correct body."""
        backend = KlingBackend(
            api_key="test-key",
            quality="720p",
            character_orientation="video",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "task-123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        backend._client = mock_client

        task_id = await backend._submit_task(
            "data:image/png;base64,ABC",
            "data:video/mp4;base64,DEF",
            0,
        )

        assert task_id == "task-123"
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/videos/generations"

        payload = call_args[1]["json"]
        assert payload["model"] == "kling-v3-motion-control"
        assert payload["image_urls"] == ["data:image/png;base64,ABC"]
        assert payload["video_urls"] == ["data:video/mp4;base64,DEF"]
        assert payload["quality"] == "720p"
        assert payload["model_params"]["character_orientation"] == "video"
        assert payload["model_params"]["keep_sound"] is False
        assert payload["model_params"]["watermark_info"]["show"] is False

    @pytest.mark.asyncio
    async def test_evolink_request_validates_avatar_size(
        self, tmp_path: Path
    ) -> None:
        """Avatar files exceeding 10MB are rejected before API call."""
        avatar = tmp_path / "avatar_large.png"
        avatar.write_bytes(b"x" * (_AVATAR_MAX_BYTES + 1))
        segment = tmp_path / "segment.mp4"
        segment.write_bytes(b"MP4_DATA")

        backend = KlingBackend(api_key="test-key")
        backend._client = AsyncMock()

        with pytest.raises(BackendError, match="Avatar file too large"):
            await backend.generate_segment(avatar, segment, 0, {})

    @pytest.mark.asyncio
    async def test_evolink_request_validates_segment_size(
        self, tmp_path: Path
    ) -> None:
        """Segment files exceeding 100MB are rejected before API call."""
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG_DATA")
        segment = tmp_path / "segment_large.mp4"
        segment.write_bytes(b"x" * (_VIDEO_MAX_BYTES + 1))

        backend = KlingBackend(api_key="test-key")
        backend._client = AsyncMock()

        with pytest.raises(BackendError, match="Segment video too large"):
            await backend.generate_segment(avatar, segment, 0, {})


class TestEvoLinkPolling:
    """Tests for the EvoLink task polling state machine."""

    @pytest.mark.asyncio
    async def test_evolink_polling_completed(self) -> None:
        """Polling returns video URL when task status is completed."""
        backend = KlingBackend(api_key="test-key")

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "id": "task-123",
            "status": "completed",
            "video_url": "https://cdn.evolink.test/result.mp4",
            "duration": 10,
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=completed_response)
        backend._client = mock_client

        url = await backend._poll_task("task-123", 0)
        assert url == "https://cdn.evolink.test/result.mp4"
        mock_client.get.assert_called_once_with("/tasks/task-123")

    @pytest.mark.asyncio
    async def test_evolink_polling_uses_correct_endpoint(self) -> None:
        """Polling GET requests use /tasks/{task_id}."""
        backend = KlingBackend(api_key="test-key")

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "id": "task-abc",
            "status": "completed",
            "video_url": "https://cdn.evolink.test/result.mp4",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=completed_response)
        backend._client = mock_client

        await backend._poll_task("task-abc", 0)
        mock_client.get.assert_called_once_with("/tasks/task-abc")

    @pytest.mark.asyncio
    async def test_evolink_polling_failed_task(self) -> None:
        """Polling raises BackendError when task status is failed."""
        backend = KlingBackend(api_key="test-key")

        failed_response = MagicMock()
        failed_response.status_code = 200
        failed_response.json.return_value = {
            "id": "task-123",
            "status": "failed",
            "error": "Model inference error",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=failed_response)
        backend._client = mock_client

        with pytest.raises(BackendError, match="failed"):
            await backend._poll_task("task-123", 0)

    @pytest.mark.asyncio
    async def test_evolink_polling_processing_then_completed(self) -> None:
        """Polling handles processing status before completion."""
        backend = KlingBackend(api_key="test-key")

        processing_response = MagicMock()
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "id": "task-123",
            "status": "processing",
        }

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "id": "task-123",
            "status": "completed",
            "video_url": "https://cdn.evolink.test/result.mp4",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[processing_response, completed_response]
        )
        backend._client = mock_client

        with patch(
            "src.infrastructure.backends.kling_backend.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            url = await backend._poll_task("task-123", 0)

        assert url == "https://cdn.evolink.test/result.mp4"
        assert mock_client.get.call_count == 2


class TestEvoLinkRetryLogic:
    """Tests for retry behaviour on rate limiting."""

    @pytest.mark.asyncio
    async def test_evolink_retry_on_429(self) -> None:
        """429 response triggers retry with exponential backoff."""
        backend = KlingBackend(api_key="test-key")

        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"id": "task-123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[rate_limited, success]
        )
        backend._client = mock_client

        with patch(
            "src.infrastructure.backends.kling_backend.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            task_id = await backend._submit_task(
                "img_uri", "vid_uri", 0
            )

        assert task_id == "task-123"
        assert mock_client.post.call_count == 2
        mock_sleep.assert_called_once()


class TestEvoLinkTimeout:
    """Tests for task timeout behaviour."""

    @pytest.mark.asyncio
    async def test_evolink_timeout_raises_backend_error(self) -> None:
        """Polling timeout raises BackendError after exceeding limit."""
        backend = KlingBackend(api_key="test-key")

        processing_response = MagicMock()
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "id": "task-forever",
            "status": "processing",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=processing_response)
        backend._client = mock_client

        with patch(
            "src.infrastructure.backends.kling_backend._POLL_TIMEOUT_SEC",
            10.0,
        ), patch(
            "src.infrastructure.backends.kling_backend._POLL_INTERVAL_SEC",
            5.0,
        ), patch(
            "src.infrastructure.backends.kling_backend.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(BackendError, match="timed out"):
                await backend._poll_task("task-forever", 0)


class TestQualityOptions:
    """Tests for quality-specific configuration."""

    def test_quality_720p_vs_1080p(self) -> None:
        """Both quality options are accepted and stored."""
        backend_720 = KlingBackend(api_key="key", quality="720p")
        backend_1080 = KlingBackend(api_key="key", quality="1080p")

        assert backend_720._quality == "720p"
        assert backend_1080._quality == "1080p"
