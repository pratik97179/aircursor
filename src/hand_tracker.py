"""MediaPipe hand landmark adapter. No interaction state."""

from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def _default_model_path():
    """Resolve hand_landmarker.task for src/ runs and installed entrypoints."""
    name = Path("models") / "hand_landmarker.task"
    candidates = [
        Path.cwd() / name,
        Path(__file__).resolve().parent.parent / name,
        Path(__file__).resolve().parent / name,
    ]

    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        candidates.append(parent / name)

    for path in candidates:
        if path.is_file():
            return path

    searched = ", ".join(str(p) for p in candidates[:5])
    raise FileNotFoundError(
        "Could not find models/hand_landmarker.task. "
        f"Run from the repo root or place the model on disk. Tried: {searched}"
    )


class HandTracker:

    def __init__(self, model_path=None):
        model_path = Path(model_path) if model_path else _default_model_path()

        base_options = python.BaseOptions(
            model_asset_path=str(model_path),
            delegate=python.BaseOptions.Delegate.CPU,
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
        )

        self.detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame, timestamp_ms):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        return self.detector.detect_for_video(image, timestamp_ms)

    def draw_landmarks(self, frame, detection_result):
        height, width, _ = frame.shape

        for hand in detection_result.hand_landmarks:
            for landmark in hand:
                x = int(landmark.x * width)
                y = int(landmark.y * height)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        return frame

    def get_control_point(self, detection_result):
        if not detection_result.hand_landmarks:
            return None

        hand = detection_result.hand_landmarks[0]
        return hand[8].x, hand[8].y
