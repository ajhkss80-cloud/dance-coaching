"""Unit tests for the fal.ai backend.

Tests mock httpx to verify correct API request format, polling
logic, and timeout handling without requiring a live API connection.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.errors import BackendError
from src.infrastructure.backends.falai_backend import FalAIBackend


class TestFalAIConstruction:
    """Tests for FalAIBackend construction."""

    def test_construction_kling_mc(self) -> None:
        """Kling V3 Standard MC model creates correct backend."""
        backend = FalAIBackend(
            api_key="fal-key-123",
            model="kling-v3-standard-mc",
        )
        assert backend._model == "kling-v3-standard-mc"
        assert backend._model_id == (
            "fal-ai/kling-video/v3/standard/motion-control"
        )

    def test_construction_kling_pro_mc(self) -> None:
        """Kling V3 Pro MC model creates correct backend."""
        backend = FalAIBackend(
            api_key="fal-key-123",
            model="kling-v3-pro-mc",
        )
        assert backend._model_id == (
            "fal-ai/kling-video/v3/pro/motion-control"
        )

    def test_construction_wan_animate(self) -> None:
        """Wan 2.2 Animate model creates correct backend."""
        backend = FalAIBackend(
            api_key="fal-key-123",
            model="wan-animate",
        )
        assert backend._model == "wan-animate"
        assert backend._model_id == "fal-ai/wan/v2.2-14b/animate/move"

    def test_name_reflects_model_kling(self) -> None:
        """Name returns falai-kling-v3-standard-mc."""
        backend = FalAIBackend(
            api_key="key", model="kling-v3-standard-mc"
        )
        assert backend.name() == "falai-kling-v3-standard-mc"

    def test_name_reflects_model_wan(self) -> None:
        """Name returns falai-wan-animate."""
        backend = FalAIBackend(api_key="key", model="wan-animate")
        assert backend.name() == "falai-wan-animate"

    def test_empty_api_key_raises(self) -> None:
        """Empty API key raises BackendError at construction."""
        with pytest.raises(BackendError, match="must not be empty"):
            FalAIBackend(api_key="")

    def test_invalid_model_raises(self) -> None:
        """Unknown model name raises BackendError at construction."""
        with pytest.raises(BackendError, match="Unknown fal.ai model"):
            FalAIBackend(api_key="key", model="nonexistent")

    def test_invalid_orientation_raises(self) -> None:
        """Invalid character_orientation raises BackendError."""
        with pytest.raises(BackendError, match="character_orientation"):
            FalAIBackend(
                api_key="key", character_orientation="invalid"
            )


class TestFalAIGeneration:
    """Tests for generate_segment lifecycle."""

    @pytest.mark.asyncio
    async def test_generate_without_initialize_raises(
        self, tmp_path: Path
    ) -> None:
        """Calling generate_segment before initialize raises BackendError."""
        backend = FalAIBackend(api_key="key")
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG")
        segment = tmp_path / "seg.mp4"
        segment.write_bytes(b"MP4")

        with pytest.raises(BackendError, match="not initialized"):
            await backend.generate_segment(avatar, segment, 0, {})

    @pytest.mark.asyncio
    async def test_cleanup_safe_when_not_initialized(self) -> None:
        """Cleanup is safe to call without initialization."""
        backend = FalAIBackend(api_key="key")
        await backend.cleanup()  # Should not raise


class TestFalAIRequestFormat:
    """Tests verifying the correct fal.ai API request format."""

    @pytest.mark.asyncio
    async def test_request_format(self) -> None:
        """Submit request posts to correct fal.ai queue endpoint."""
        backend = FalAIBackend(
            api_key="fal-key",
            model="kling-v3-standard-mc",
            character_orientation="video",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"request_id": "req-xyz"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        backend._client = mock_client

        request_id = await backend._submit_request(
            "data:image/png;base64,ABC",
            "data:video/mp4;base64,DEF",
            0,
        )

        assert request_id == "req-xyz"
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        expected_url = (
            "https://queue.fal.run/"
            "fal-ai/kling-video/v3/standard/motion-control"
        )
        assert call_args[0][0] == expected_url

        payload = call_args[1]["json"]
        assert payload["image_url"] == "data:image/png;base64,ABC"
        assert payload["video_url"] == "data:video/mp4;base64,DEF"
        assert payload["character_orientation"] == "video"


class TestFalAIPolling:
    """Tests for the request polling logic."""

    @pytest.mark.asyncio
    async def test_polling_completed(self) -> None:
        """Polling returns without error when status is COMPLETED."""
        backend = FalAIBackend(api_key="key")

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "status": "COMPLETED",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=completed_response)
        backend._client = mock_client

        # Should not raise
        await backend._poll_status("req-abc", 0)

        expected_url = (
            "https://queue.fal.run/"
            "fal-ai/kling-video/v3/standard/motion-control"
            "/requests/req-abc/status"
        )
        mock_client.get.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_polling_timeout(self) -> None:
        """Polling raises BackendError after timeout."""
        backend = FalAIBackend(api_key="key")

        processing_response = MagicMock()
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "status": "IN_PROGRESS",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=processing_response)
        backend._client = mock_client

        with patch(
            "src.infrastructure.backends.falai_backend._POLL_TIMEOUT_SEC",
            10.0,
        ), patch(
            "src.infrastructure.backends.falai_backend._POLL_INTERVAL_SEC",
            5.0,
        ), patch(
            "src.infrastructure.backends.falai_backend.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(BackendError, match="timed out"):
                await backend._poll_status("req-forever", 0)

    @pytest.mark.asyncio
    async def test_polling_failed(self) -> None:
        """Polling raises BackendError when status is FAILED."""
        backend = FalAIBackend(api_key="key")

        failed_response = MagicMock()
        failed_response.status_code = 200
        failed_response.json.return_value = {
            "status": "FAILED",
            "error": "Model error",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=failed_response)
        backend._client = mock_client

        with pytest.raises(BackendError, match="failed"):
            await backend._poll_status("req-fail", 0)


class TestFalAIResult:
    """Tests for result retrieval."""

    @pytest.mark.asyncio
    async def test_get_result_extracts_video_url(self) -> None:
        """Result retrieval extracts video URL from nested structure."""
        backend = FalAIBackend(api_key="key")

        result_response = MagicMock()
        result_response.status_code = 200
        result_response.json.return_value = {
            "video": {"url": "https://cdn.fal.test/result.mp4"},
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=result_response)
        backend._client = mock_client

        url = await backend._get_result("req-abc", 0)
        assert url == "https://cdn.fal.test/result.mp4"
