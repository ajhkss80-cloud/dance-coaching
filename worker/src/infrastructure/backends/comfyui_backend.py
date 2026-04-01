"""ComfyUI API backend for video generation.

Implements the GenerationBackend ABC by communicating with a locally
running ComfyUI server via its REST API. This allows using any
ComfyUI workflow (SteadyDancer, SCAIL, Wan2.2 Animate, etc.) as
the generation engine without directly loading models in this process.

The ComfyUI server handles GPU management, model loading, and inference.
This backend simply submits workflow requests and retrieves results.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path

from src.application.ports.generation_backend import GenerationBackend
from src.domain.errors import BackendError

logger = logging.getLogger(__name__)

# Default workflow template for dance motion transfer
# Uses DWPose extraction → model inference → video output
# The {placeholders} are replaced at runtime
DEFAULT_WORKFLOW_TEMPLATE = {
    "description": "Dance motion transfer workflow",
    "nodes": {
        "load_image": {
            "class_type": "LoadImage",
            "inputs": {"image": "{avatar_filename}"},
        },
        "load_video": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": "{segment_filename}",
                "force_rate": 0,
                "force_size": "Disabled",
                "frame_load_cap": 0,
            },
        },
        "dwpose": {
            "class_type": "DWPreprocessor",
            "inputs": {
                "image": ["load_video", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": 768,
            },
        },
        "animate": {
            "class_type": "{model_node_class}",
            "inputs": {
                "image": ["load_image", 0],
                "pose_video": ["dwpose", 0],
                "steps": "{inference_steps}",
                "seed": "{seed}",
            },
        },
        "save_video": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["animate", 0],
                "frame_rate": 30,
                "format": "video/h264-mp4",
                "filename_prefix": "{output_prefix}",
            },
        },
    },
}


class ComfyUIBackend(GenerationBackend):
    """Generation backend that delegates to a ComfyUI API server.

    Submits workflow requests to ComfyUI's REST API and polls for
    completion. The actual model inference (SteadyDancer, SCAIL,
    Wan2.2 Animate, etc.) runs inside ComfyUI.

    Attributes:
        base_url: ComfyUI server URL (e.g., http://localhost:8188).
        workflow_template: Path to a custom workflow JSON, or None
            to use the default template.
        model_node_class: The ComfyUI node class for the animation
            model (e.g., 'SteadyDancerBasic', 'WanVideoAnimate').
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        workflow_template: str | None = None,
        model_node_class: str = "SteadyDancerBasic",
        inference_steps: int = 50,
        seed: int = 42,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._workflow_template_path = workflow_template
        self._model_node_class = model_node_class
        self._inference_steps = inference_steps
        self._seed = seed
        self._client = None
        self._client_id = str(uuid.uuid4())
        self._workflow: dict | None = None

    async def initialize(self) -> None:
        """Connect to ComfyUI server and validate it is running.

        Loads the workflow template (custom or default) and verifies
        the ComfyUI API is reachable.

        Raises:
            BackendError: If ComfyUI server is not reachable or
                workflow template is invalid.
        """
        try:
            import httpx
        except ImportError:
            raise BackendError(
                "httpx is required for ComfyUI backend. "
                "Install with: pip install httpx"
            )

        self._client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

        # Test connectivity
        try:
            resp = await self._client.get(f"{self._base_url}/system_stats")
            resp.raise_for_status()
            stats = resp.json()
            logger.info(
                "Connected to ComfyUI server at %s (devices: %s)",
                self._base_url,
                [d.get("name", "unknown") for d in stats.get("devices", [])],
            )
        except httpx.ConnectError:
            raise BackendError(
                f"Cannot connect to ComfyUI server at {self._base_url}. "
                "Ensure ComfyUI is running with: python main.py --listen 0.0.0.0"
            )
        except Exception as exc:
            raise BackendError(
                f"ComfyUI server health check failed: {exc}"
            )

        # Load workflow template
        if self._workflow_template_path:
            template_path = Path(self._workflow_template_path)
            if not template_path.exists():
                raise BackendError(
                    f"Workflow template not found: {template_path}"
                )
            try:
                self._workflow = json.loads(template_path.read_text())
                logger.info("Loaded custom workflow from %s", template_path)
            except json.JSONDecodeError as exc:
                raise BackendError(
                    f"Invalid workflow JSON in {template_path}: {exc}"
                )
        else:
            self._workflow = DEFAULT_WORKFLOW_TEMPLATE
            logger.info(
                "Using default workflow template (model: %s)",
                self._model_node_class,
            )

    async def generate_segment(
        self,
        avatar_path: Path,
        segment_path: Path,
        segment_index: int,
        options: dict,
    ) -> Path:
        """Generate a video segment by submitting a workflow to ComfyUI.

        Uploads the avatar image and reference segment to ComfyUI,
        submits the workflow, polls for completion, and downloads
        the result.

        Args:
            avatar_path: Path to the avatar image file.
            segment_path: Path to the reference video segment.
            segment_index: Zero-based index of this segment.
            options: Additional options. Supported keys:
                - inference_steps (int): Override default steps.
                - seed (int): Override default seed.
                - model_node_class (str): Override model node.

        Returns:
            Path to the generated video segment.

        Raises:
            BackendError: If generation fails or times out.
        """
        if self._client is None:
            raise BackendError(
                "Backend not initialized. Call initialize() first."
            )

        logger.info(
            "Generating segment %d via ComfyUI (%s)",
            segment_index,
            self._model_node_class,
        )

        try:
            # Step 1: Upload files to ComfyUI
            avatar_filename = await self._upload_file(
                avatar_path, subfolder="input"
            )
            segment_filename = await self._upload_file(
                segment_path, subfolder="input"
            )

            # Step 2: Build workflow with actual filenames
            output_prefix = f"dance_seg{segment_index}_{uuid.uuid4().hex[:8]}"
            workflow = self._build_workflow(
                avatar_filename=avatar_filename,
                segment_filename=segment_filename,
                output_prefix=output_prefix,
                inference_steps=options.get(
                    "inference_steps", self._inference_steps
                ),
                seed=options.get("seed", self._seed + segment_index),
                model_node_class=options.get(
                    "model_node_class", self._model_node_class
                ),
            )

            # Step 3: Queue the workflow
            prompt_id = await self._queue_prompt(workflow)
            logger.info(
                "Segment %d queued with prompt_id: %s",
                segment_index,
                prompt_id,
            )

            # Step 4: Poll for completion
            output_data = await self._poll_completion(
                prompt_id, timeout_sec=600
            )

            # Step 5: Download result video
            output_path = await self._download_result(
                output_data, output_prefix, segment_index
            )

            logger.info(
                "Segment %d generated: %s", segment_index, output_path
            )
            return output_path

        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(
                f"ComfyUI generation failed for segment {segment_index}: {exc}"
            )

    async def cleanup(self) -> None:
        """Close the HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info("ComfyUI backend cleaned up")

    def name(self) -> str:
        """Return the backend name including the model being used."""
        return f"comfyui-{self._model_node_class}"

    # --- Private methods ---

    async def _upload_file(
        self, file_path: Path, subfolder: str = "input"
    ) -> str:
        """Upload a file to ComfyUI's input directory.

        Args:
            file_path: Local path to the file.
            subfolder: ComfyUI subfolder ('input', 'temp', etc.).

        Returns:
            The filename as stored on the ComfyUI server.

        Raises:
            BackendError: If upload fails.
        """
        if not file_path.exists():
            raise BackendError(f"File not found: {file_path}")

        try:
            with open(file_path, "rb") as f:
                resp = await self._client.post(
                    f"{self._base_url}/upload/image",
                    files={"image": (file_path.name, f, "application/octet-stream")},
                    data={"subfolder": subfolder, "overwrite": "true"},
                )
                resp.raise_for_status()
                result = resp.json()
                return result.get("name", file_path.name)
        except Exception as exc:
            raise BackendError(f"Failed to upload {file_path.name}: {exc}")

    def _build_workflow(
        self,
        avatar_filename: str,
        segment_filename: str,
        output_prefix: str,
        inference_steps: int,
        seed: int,
        model_node_class: str,
    ) -> dict:
        """Build a ComfyUI API-format workflow from the template.

        Replaces placeholder values in the template with actual
        runtime values.

        Returns:
            A workflow dict ready for submission to ComfyUI's /prompt API.
        """
        workflow_json = json.dumps(self._workflow)
        workflow_json = workflow_json.replace(
            "{avatar_filename}", avatar_filename
        )
        workflow_json = workflow_json.replace(
            "{segment_filename}", segment_filename
        )
        workflow_json = workflow_json.replace(
            "{output_prefix}", output_prefix
        )
        workflow_json = workflow_json.replace(
            "{inference_steps}", str(inference_steps)
        )
        workflow_json = workflow_json.replace("{seed}", str(seed))
        workflow_json = workflow_json.replace(
            "{model_node_class}", model_node_class
        )
        return json.loads(workflow_json)

    async def _queue_prompt(self, workflow: dict) -> str:
        """Submit a workflow to ComfyUI's prompt queue.

        Args:
            workflow: The workflow dict to execute.

        Returns:
            The prompt_id assigned by ComfyUI.

        Raises:
            BackendError: If queuing fails.
        """
        payload = {
            "prompt": workflow.get("nodes", workflow),
            "client_id": self._client_id,
        }

        try:
            resp = await self._client.post(
                f"{self._base_url}/prompt", json=payload
            )
            resp.raise_for_status()
            result = resp.json()
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                raise BackendError(
                    f"No prompt_id in ComfyUI response: {result}"
                )
            return prompt_id
        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(f"Failed to queue ComfyUI prompt: {exc}")

    async def _poll_completion(
        self, prompt_id: str, timeout_sec: int = 600
    ) -> dict:
        """Poll ComfyUI history until the prompt completes or times out.

        Args:
            prompt_id: The prompt ID to monitor.
            timeout_sec: Maximum seconds to wait.

        Returns:
            The output data dict from the completed prompt.

        Raises:
            BackendError: If the prompt fails or times out.
        """
        elapsed = 0
        poll_interval = 3

        while elapsed < timeout_sec:
            try:
                resp = await self._client.get(
                    f"{self._base_url}/history/{prompt_id}"
                )
                resp.raise_for_status()
                history = resp.json()

                if prompt_id in history:
                    entry = history[prompt_id]
                    status = entry.get("status", {})

                    if status.get("completed", False):
                        outputs = entry.get("outputs", {})
                        logger.info("Prompt %s completed", prompt_id)
                        return outputs

                    if status.get("status_str") == "error":
                        messages = entry.get("status", {}).get(
                            "messages", []
                        )
                        raise BackendError(
                            f"ComfyUI prompt failed: {messages}"
                        )

            except BackendError:
                raise
            except Exception:
                pass

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise BackendError(
            f"ComfyUI prompt {prompt_id} timed out after {timeout_sec}s"
        )

    async def _download_result(
        self, outputs: dict, output_prefix: str, segment_index: int
    ) -> Path:
        """Download the generated video from ComfyUI's output.

        Searches the prompt outputs for a video file matching the
        expected prefix, then downloads it to a local temp path.

        Args:
            outputs: The outputs dict from ComfyUI history.
            output_prefix: The filename prefix used during generation.
            segment_index: Segment index for naming.

        Returns:
            Path to the downloaded video file.

        Raises:
            BackendError: If no output video is found or download fails.
        """
        # Find the video output across all output nodes
        for node_id, node_output in outputs.items():
            gifs = node_output.get("gifs", [])
            videos = node_output.get("videos", [])
            images = node_output.get("images", [])

            for file_info in gifs + videos + images:
                filename = file_info.get("filename", "")
                subfolder = file_info.get("subfolder", "")
                file_type = file_info.get("type", "output")

                if (
                    filename.startswith(output_prefix)
                    or filename.endswith(".mp4")
                    or filename.endswith(".webm")
                ):
                    return await self._download_file(
                        filename, subfolder, file_type, segment_index
                    )

        raise BackendError(
            f"No video output found for prefix '{output_prefix}' "
            f"in ComfyUI outputs: {list(outputs.keys())}"
        )

    async def _download_file(
        self,
        filename: str,
        subfolder: str,
        file_type: str,
        segment_index: int,
    ) -> Path:
        """Download a single file from ComfyUI's view endpoint.

        Args:
            filename: The file's name on the ComfyUI server.
            subfolder: The subfolder within ComfyUI's output.
            file_type: 'output', 'temp', or 'input'.
            segment_index: Segment index for local naming.

        Returns:
            Path to the locally saved file.

        Raises:
            BackendError: If download fails.
        """
        import tempfile

        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": file_type,
        }

        try:
            resp = await self._client.get(
                f"{self._base_url}/view", params=params
            )
            resp.raise_for_status()

            suffix = Path(filename).suffix or ".mp4"
            output_path = Path(
                tempfile.mktemp(
                    suffix=suffix,
                    prefix=f"comfyui_seg{segment_index}_",
                )
            )
            output_path.write_bytes(resp.content)
            return output_path

        except Exception as exc:
            raise BackendError(
                f"Failed to download {filename} from ComfyUI: {exc}"
            )
