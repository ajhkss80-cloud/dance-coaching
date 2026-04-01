"""Unit tests for the WaveSpeed AI backend.

Tests mock httpx to verify correct API request format, polling
logic, and timeout handling without requiring a live API connection.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.errors import BackendError
from src.infrastructure.backends.wavespeed_backend import (
    WaveSpeedBackend,
    _POLL_TIMEOUT_SEC,
)


class TestWaveSpeedConstruction:
    """Tests for WaveSpeedBackend construction."""

    def test_construction_steady_dancer(self) -> None:
        """SteadyDancer model creates correct backend."""
        backend = WaveSpeedBackend(
            api_key="ws-key-123",
            model="steady-dancer",
            resolution="720p",
        )
        assert backend._model == "steady-dancer"
        assert backend._model_path == "wavespeed-ai/steady-dancer"
        assert backend._resolution == "720p"

    def test_construction_wan_animate(self) -> None:
        """Wan 2.2 Animate model creates correct backend."""
        backend = WaveSpeedBackend(
            api_key="ws-key-123",
            model="wan-animate",
            resolution="480p",
        )
        assert backend._model == "wan-animate"
        assert backend._model_path == "wavespeed-ai/wan-2.2/animate"
        assert backend._resolution == "480p"

    def test_name_reflects_model_steady_dancer(self) -> None:
        """Name returns wavespeed-steady-dancer for SteadyDancer model."""
        backend = WaveSpeedBackend(api_key="key", model="steady-dancer")
        assert backend.name() == "wavespeed-steady-dancer"

    def test_name_reflects_model_wan_animate(self) -> None:
        """Name returns wavespeed-wan-animate for Wan Animate model."""
        backend = WaveSpeedBackend(api_key="key", model="wan-animate")
        assert backend.name() == "wavespeed-wan-animate"

    def test_empty_api_key_raises(self) -> None:
        """Empty API key raises BackendError at construction."""
        with pytest.raises(BackendError, match="must not be empty"):
            WaveSpeedBackend(api_key="")

    def test_invalid_model_raises(self) -> None:
        """Unknown model name raises BackendError at construction."""
        with pytest.raises(BackendError, match="Unknown WaveSpeed model"):
            WaveSpeedBackend(api_key="key", model="nonexistent")

    def test_invalid_resolution_raises(self) -> None:
        """Invalid resolution raises BackendError at construction."""
        with pytest.raises(BackendError, match="Resolution must be"):
            WaveSpeedBackend(api_key="key", resolution="1080p")


class TestWaveSpeedGeneration:
    """Tests for generate_segment lifecycle."""

    @pytest.mark.asyncio
    async def test_generate_without_initialize_raises(
        self, tmp_path: Path
    ) -> None:
        """Calling generate_segment before initialize raises BackendError."""
        backend = WaveSpeedBackend(api_key="key")
        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG")
        segment = tmp_path / "seg.mp4"
        segment.write_bytes(b"MP4")

        with pytest.raises(BackendError, match="not initialized"):
            await backend.generate_segment(avatar, segment, 0, {})

    @pytest.mark.asyncio
    async def test_cleanup_safe_when_not_initialized(self) -> None:
        """Cleanup is safe to call without initialization."""
        backend = WaveSpeedBackend(api_key="key")
        await backend.cleanup()  # Should not raise


class TestWaveSpeedRequestFormat:
    """Tests verifying the correct WaveSpeed API request format."""

    @pytest.mark.asyncio
    async def test_request_format(self) -> None:
        """Submit request posts to correct URL with correct body."""
        backend = WaveSpeedBackend(
            api_key="ws-key",
            model="steady-dancer",
            resolution="720p",
            base_url="https://api.wavespeed.test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "req-abc"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        backend._client = mock_client

        request_id = await backend._submit_request(
            "data:image/png;base64,ABC",
            "data:video/mp4;base64,DEF",
            0,
        )

        assert request_id == "req-abc"
        mock_client.post.assert_called_once()

        call_args = mock_client.post.call_args
        assert call_args[0][0] == (
            "https://api.wavespeed.test/api/v3/wavespeed-ai/steady-dancer"
        )
        payload = call_args[1]["json"]
        assert payload["image"] == "data:image/png;base64,ABC"
        assert payload["video"] == "data:video/mp4;base64,DEF"
        assert payload["resolution"] == "720p"


class TestWaveSpeedPolling:
    """Tests for the request polling logic."""

    @pytest.mark.asyncio
    async def test_polling_completed(self) -> None:
        """Polling returns video URL when status is completed."""
        backend = WaveSpeedBackend(
            api_key="key",
            base_url="https://api.wavespeed.test",
        )

        completed_response = MagicMock()
        completed_response.status_code = 200
        completed_response.json.return_value = {
            "status": "completed",
            "output": {"video_url": "https://cdn.test/result.mp4"},
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=completed_response)
        backend._client = mock_client

        url = await backend._poll_result("req-abc", 0)
        assert url == "https://cdn.test/result.mp4"
        mock_client.get.assert_called_once_with(
            "https://api.wavespeed.test/api/v3/predictions/req-abc/result"
        )

    @pytest.mark.asyncio
    async def test_polling_timeout(self) -> None:
        """Polling raises BackendError after timeout."""
        backend = WaveSpeedBackend(
            api_key="key",
            base_url="https://api.wavespeed.test",
        )

        processing_response = MagicMock()
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "status": "processing",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=processing_response)
        backend._client = mock_client

        with patch(
            "src.infrastructure.backends.wavespeed_backend._POLL_TIMEOUT_SEC",
            10.0,
        ), patch(
            "src.infrastructure.backends.wavespeed_backend._POLL_INTERVAL_SEC",
            5.0,
        ), patch(
            "src.infrastructure.backends.wavespeed_backend.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(BackendError, match="timed out"):
                await backend._poll_result("req-forever", 0)

    @pytest.mark.asyncio
    async def test_polling_failed(self) -> None:
        """Polling raises BackendError when status is failed."""
        backend = WaveSpeedBackend(
            api_key="key",
            base_url="https://api.wavespeed.test",
        )

        failed_response = MagicMock()
        failed_response.status_code = 200
        failed_response.json.return_value = {
            "status": "failed",
            "error": "Model inference error",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=failed_response)
        backend._client = mock_client

        with pytest.raises(BackendError, match="failed"):
            await backend._poll_result("req-fail", 0)
