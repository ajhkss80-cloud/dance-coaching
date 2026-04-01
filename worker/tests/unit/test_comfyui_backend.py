"""Unit tests for ComfyUIBackend.

Tests the ComfyUI API interaction logic using httpx mock responses.
Does NOT require a running ComfyUI server.
"""
from __future__ import annotations

import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.backends.comfyui_backend import ComfyUIBackend
from src.domain.errors import BackendError


class TestComfyUIConstruction:
    """Tests for ComfyUIBackend construction and initialization."""

    def test_default_construction(self):
        backend = ComfyUIBackend()
        assert backend.name() == "comfyui-SteadyDancerBasic"
        assert backend._base_url == "http://localhost:8188"
        assert backend._inference_steps == 50

    def test_custom_model_name(self):
        backend = ComfyUIBackend(model_node_class="WanVideoAnimate")
        assert backend.name() == "comfyui-WanVideoAnimate"

    def test_custom_url(self):
        backend = ComfyUIBackend(base_url="http://gpu-server:8188/")
        assert backend._base_url == "http://gpu-server:8188"

    def test_custom_inference_steps(self):
        backend = ComfyUIBackend(inference_steps=75)
        assert backend._inference_steps == 75

    @pytest.mark.asyncio
    async def test_generate_without_initialize_raises(self, tmp_path):
        backend = ComfyUIBackend()
        with pytest.raises(BackendError, match="not initialized"):
            await backend.generate_segment(
                tmp_path / "avatar.png",
                tmp_path / "seg.mp4",
                0,
                {},
            )

    @pytest.mark.asyncio
    async def test_cleanup_safe_when_not_initialized(self):
        backend = ComfyUIBackend()
        await backend.cleanup()  # Should not raise


class TestComfyUIInitialize:
    """Tests for ComfyUI server connectivity check."""

    @pytest.mark.asyncio
    async def test_initialize_connects_to_server(self):
        backend = ComfyUIBackend()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "devices": [{"name": "NVIDIA RTX 5080", "vram_total": 16e9}]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            await backend.initialize()
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_fails_on_connection_error(self):
        backend = ComfyUIBackend()

        import httpx

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            MockClient.return_value = mock_client

            with pytest.raises(BackendError, match="Cannot connect"):
                await backend.initialize()

    @pytest.mark.asyncio
    async def test_initialize_with_custom_workflow_missing_file(self):
        backend = ComfyUIBackend(
            workflow_template="/nonexistent/workflow.json"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"devices": []}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            with pytest.raises(BackendError, match="not found"):
                await backend.initialize()

    @pytest.mark.asyncio
    async def test_initialize_with_custom_workflow_file(self, tmp_path):
        workflow_file = tmp_path / "custom.json"
        workflow_file.write_text(json.dumps({"nodes": {"test": {}}}))

        backend = ComfyUIBackend(
            workflow_template=str(workflow_file)
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"devices": []}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            await backend.initialize()
            assert backend._workflow == {"nodes": {"test": {}}}


class TestComfyUIWorkflowBuilding:
    """Tests for workflow template interpolation."""

    def test_build_workflow_replaces_placeholders(self):
        backend = ComfyUIBackend()
        backend._workflow = {
            "nodes": {
                "load": {"inputs": {"image": "{avatar_filename}"}},
                "model": {"class_type": "{model_node_class}"},
                "settings": {"steps": "{inference_steps}", "seed": "{seed}"},
                "save": {"inputs": {"filename_prefix": "{output_prefix}"}},
            }
        }

        result = backend._build_workflow(
            avatar_filename="test_avatar.png",
            segment_filename="test_seg.mp4",
            output_prefix="dance_seg0_abc",
            inference_steps=50,
            seed=42,
            model_node_class="SteadyDancerBasic",
        )

        assert result["nodes"]["load"]["inputs"]["image"] == "test_avatar.png"
        assert result["nodes"]["model"]["class_type"] == "SteadyDancerBasic"
        assert result["nodes"]["settings"]["steps"] == "50"
        assert result["nodes"]["settings"]["seed"] == "42"
        assert result["nodes"]["save"]["inputs"]["filename_prefix"] == "dance_seg0_abc"


class TestComfyUIPolling:
    """Tests for prompt completion polling."""

    @pytest.mark.asyncio
    async def test_poll_completed(self):
        backend = ComfyUIBackend()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "test-prompt-id": {
                "status": {"completed": True},
                "outputs": {"node1": {"videos": [{"filename": "out.mp4"}]}},
            }
        }

        backend._client = AsyncMock()
        backend._client.get = AsyncMock(return_value=mock_response)

        result = await backend._poll_completion("test-prompt-id", timeout_sec=10)
        assert "node1" in result

    @pytest.mark.asyncio
    async def test_poll_timeout(self):
        backend = ComfyUIBackend()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        backend._client = AsyncMock()
        backend._client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(BackendError, match="timed out"):
            await backend._poll_completion("test-id", timeout_sec=1)

    @pytest.mark.asyncio
    async def test_poll_error_status(self):
        backend = ComfyUIBackend()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "test-id": {
                "status": {"status_str": "error", "messages": ["OOM"]},
            }
        }

        backend._client = AsyncMock()
        backend._client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(BackendError, match="prompt failed"):
            await backend._poll_completion("test-id", timeout_sec=10)


class TestContainerComfyUIIntegration:
    """Tests that the DI container correctly creates ComfyUI backend."""

    def test_comfyui_backend_selection(self):
        from src.infrastructure.config import WorkerConfig
        from src.di.container import create_container
        from src.infrastructure.backends.comfyui_backend import ComfyUIBackend
        from tests.harness.fake_backend import FakeBackend

        config = WorkerConfig(
            GENERATION_BACKEND="comfyui",
            COMFYUI_URL="http://localhost:8188",
            COMFYUI_MODEL_NODE_CLASS="SCAIL",
            COMFYUI_INFERENCE_STEPS=75,
        )

        # Use overrides for non-backend deps to avoid import issues
        from tests.harness.fake_audio_processor import FakeAudioProcessor
        from tests.harness.fake_pose_extractor import FakePoseExtractor
        from tests.harness.fake_stitcher import FakeStitcher, FakeInterpolator

        container = create_container(
            config,
            audio_processor_override=FakeAudioProcessor(),
            pose_extractor_override=FakePoseExtractor(),
            stitcher_override=FakeStitcher(),
            interpolator_override=FakeInterpolator(),
        )

        assert isinstance(container.backend, ComfyUIBackend)
        assert container.backend.name() == "comfyui-SCAIL"
        assert container.backend._inference_steps == 75

    def test_config_accepts_comfyui_backend(self):
        from src.infrastructure.config import WorkerConfig

        config = WorkerConfig(GENERATION_BACKEND="comfyui")
        assert config.GENERATION_BACKEND == "comfyui"

    def test_config_rejects_invalid_backend(self):
        from src.infrastructure.config import WorkerConfig

        with pytest.raises(ValueError, match="GENERATION_BACKEND"):
            WorkerConfig(GENERATION_BACKEND="invalid")


class TestFakeComfyUIBackend:
    """Tests for the FakeComfyUIBackend test harness."""

    @pytest.mark.asyncio
    async def test_fake_backend_records_calls(self, tmp_path):
        from tests.harness.fake_comfyui_backend import FakeComfyUIBackend

        backend = FakeComfyUIBackend(model_name="SCAIL")
        await backend.initialize()

        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG")
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"MP4")

        result = await backend.generate_segment(avatar, seg, 0, {})
        assert result.exists()
        assert len(backend.call_log) == 1
        assert backend.call_log[0]["segment_index"] == 0

    @pytest.mark.asyncio
    async def test_fake_backend_failure_simulation(self, tmp_path):
        from tests.harness.fake_comfyui_backend import FakeComfyUIBackend

        backend = FakeComfyUIBackend(fail_on_segments=[1])
        await backend.initialize()

        avatar = tmp_path / "avatar.png"
        avatar.write_bytes(b"PNG")
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"MP4")

        await backend.generate_segment(avatar, seg, 0, {})
        with pytest.raises(BackendError, match="segment 1"):
            await backend.generate_segment(avatar, seg, 1, {})

    @pytest.mark.asyncio
    async def test_fake_backend_name(self):
        from tests.harness.fake_comfyui_backend import FakeComfyUIBackend

        backend = FakeComfyUIBackend(model_name="WanVideoAnimate")
        assert backend.name() == "comfyui-WanVideoAnimate"
