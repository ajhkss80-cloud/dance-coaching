"""Fake pose extractor for testing.

Generates synthetic pose data with deterministic sine-wave motion
patterns suitable for unit and integration testing.
"""
from __future__ import annotations

from math import sin
from pathlib import Path

from src.application.ports.pose_extractor import PoseExtractor
from src.domain.value_objects import PoseFrame


class FakePoseExtractor(PoseExtractor):
    """In-memory test double for PoseExtractor.

    Generates synthetic pose frames with smooth sine-wave motion
    to simulate realistic pose extraction without requiring actual
    video processing or MediaPipe.

    Attributes:
        num_frames: Number of frames to generate per video.
        fps: Simulated frames per second for timestamp calculation.
    """

    def __init__(self, num_frames: int = 90, fps: int = 30) -> None:
        self.num_frames = num_frames
        self.fps = fps

    def extract_from_video(self, video_path: Path) -> list[PoseFrame]:
        """Generate synthetic pose data with sine-wave motion.

        Each joint oscillates slightly in x and y to simulate
        natural body movement patterns. The motion is deterministic
        and reproducible for test assertions.

        Args:
            video_path: Path to the video file (not read in fake).

        Returns:
            A list of PoseFrame objects with synthetic keypoint data.
        """
        frames: list[PoseFrame] = []

        for i in range(self.num_frames):
            t = i / self.fps
            keypoints: list[tuple[float, float, float, float]] = []

            for j in range(33):
                x = 0.5 + 0.1 * sin(t * 2.0 + j * 0.1)
                y = 0.5 + 0.05 * j / 33.0
                z = 0.0
                visibility = 0.99
                keypoints.append((x, y, z, visibility))

            frames.append(PoseFrame(timestamp=t, keypoints=keypoints))

        return frames
