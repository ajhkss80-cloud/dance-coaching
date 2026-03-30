"""MediaPipe-based pose extractor implementation.

Uses MediaPipe Pose with model_complexity=2 for high-accuracy
skeletal keypoint extraction from dance video frames.
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.application.ports.pose_extractor import PoseExtractor
from src.domain.errors import PipelineError, ValidationError
from src.domain.value_objects import PoseFrame

logger = logging.getLogger(__name__)


class MediaPipeExtractor(PoseExtractor):
    """Pose extractor using Google MediaPipe Pose.

    Processes each frame of a video file through the MediaPipe Pose
    model to extract 33 skeletal landmarks per frame.
    """

    def __init__(self, model_complexity: int = 2) -> None:
        self._model_complexity = model_complexity

    def extract_from_video(self, video_path: Path) -> list[PoseFrame]:
        """Extract pose keypoints from every frame of a video.

        Opens the video with OpenCV, processes each frame through
        MediaPipe Pose, and collects the 33 landmarks as PoseFrame
        value objects. Frames where no pose is detected reuse the
        most recent valid pose to prevent gaps.

        Args:
            video_path: Path to the input video file.

        Returns:
            A list of PoseFrame objects ordered chronologically.

        Raises:
            ValidationError: If the video file does not exist.
            PipelineError: If the video cannot be opened or processed.
        """
        if not video_path.exists():
            raise ValidationError(f"Video file not found: {video_path}")

        try:
            import cv2
        except ImportError:
            raise PipelineError(
                "opencv-python is not installed. "
                "Install with: pip install opencv-python-headless"
            )

        try:
            import mediapipe as mp
        except ImportError:
            raise PipelineError(
                "mediapipe is not installed. "
                "Install with: pip install mediapipe"
            )

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise PipelineError(f"Failed to open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
            logger.warning(
                "Could not determine FPS for %s, defaulting to %.0f",
                video_path, fps,
            )

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(
            "Processing video: %s (%d frames @ %.1f fps)",
            video_path, total_frames, fps,
        )

        mp_pose = mp.solutions.pose
        frames: list[PoseFrame] = []
        last_valid_keypoints: list[tuple[float, float, float, float]] | None = None
        skipped_count = 0

        try:
            with mp_pose.Pose(
                static_image_mode=False,
                model_complexity=self._model_complexity,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            ) as pose:
                frame_index = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    timestamp = frame_index / fps

                    # MediaPipe expects RGB input
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = pose.process(rgb_frame)

                    if results.pose_landmarks is not None:
                        keypoints = [
                            (
                                lm.x,
                                lm.y,
                                lm.z,
                                lm.visibility,
                            )
                            for lm in results.pose_landmarks.landmark
                        ]
                        last_valid_keypoints = keypoints
                    elif last_valid_keypoints is not None:
                        # Reuse last valid pose when detection fails
                        keypoints = last_valid_keypoints
                        skipped_count += 1
                    else:
                        # No valid pose detected yet; skip frame
                        frame_index += 1
                        skipped_count += 1
                        continue

                    frames.append(
                        PoseFrame(timestamp=timestamp, keypoints=keypoints)
                    )
                    frame_index += 1
        finally:
            cap.release()

        if not frames:
            raise PipelineError(
                f"No poses detected in any frame of {video_path}"
            )

        if skipped_count > 0:
            logger.warning(
                "Filled %d frames with previous pose data (no detection)",
                skipped_count,
            )

        logger.info(
            "Pose extraction complete: %d frames from %s",
            len(frames), video_path,
        )

        return frames
