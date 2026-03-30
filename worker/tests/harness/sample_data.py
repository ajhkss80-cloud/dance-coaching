"""Sample data generators for testing.

Utility functions that create minimal but valid media files
(images, videos, audio) for use in integration and E2E tests
without requiring real media assets.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from scipy.io import wavfile


def create_sample_avatar(path: Path, size: tuple[int, int] = (64, 64)) -> Path:
    """Create a simple colored PNG image as a test avatar.

    Generates a solid-color image with a centered circle to simulate
    a basic avatar photo.

    Args:
        path: Output path for the PNG file.
        size: Image dimensions as (width, height).

    Returns:
        The path to the created image file.
    """
    width, height = size
    # Create a blue background with a skin-colored circle
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = (180, 130, 70)  # BGR: medium blue background

    center = (width // 2, height // 2)
    radius = min(width, height) // 3
    cv2.circle(image, center, radius, (200, 180, 160), -1)  # BGR: skin tone

    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)
    return path


def create_sample_video(
    path: Path,
    duration: float = 3.0,
    fps: int = 30,
    size: tuple[int, int] = (64, 64),
) -> Path:
    """Create a minimal MP4 video with colored frames.

    Generates frames with a color gradient that shifts over time,
    providing a visible temporal progression for visual verification.

    Args:
        path: Output path for the MP4 file.
        duration: Video duration in seconds.
        fps: Frames per second.
        size: Frame dimensions as (width, height).

    Returns:
        The path to the created video file.
    """
    width, height = size
    total_frames = int(duration * fps)

    path.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))

    try:
        for i in range(total_frames):
            # Create a frame with color that shifts over time
            hue = int(180 * i / total_frames)  # 0-180 for OpenCV HSV
            hsv = np.full((height, width, 3), (hue, 200, 200), dtype=np.uint8)
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            writer.write(bgr)
    finally:
        writer.release()

    return path


def create_sample_audio(
    path: Path,
    duration: float = 3.0,
    sr: int = 22050,
) -> Path:
    """Create a simple WAV file with a sine wave tone.

    Generates a 440 Hz sine wave (concert A) at moderate amplitude
    for use in audio processing tests.

    Args:
        path: Output path for the WAV file.
        duration: Audio duration in seconds.
        sr: Sample rate in Hz.

    Returns:
        The path to the created audio file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    num_samples = int(duration * sr)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # 440 Hz sine wave at 50% amplitude
    frequency = 440.0
    amplitude = 0.5
    samples = amplitude * np.sin(2.0 * np.pi * frequency * t)

    # Convert to 16-bit PCM
    pcm_data = (samples * 32767).astype(np.int16)
    wavfile.write(str(path), sr, pcm_data)

    return path
