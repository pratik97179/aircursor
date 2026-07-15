"""MediaPipe hand landmark adapter. No interaction state."""

from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import config


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
            num_hands=config.NUM_HANDS,
        )

        self.detector = vision.HandLandmarker.create_from_options(options)
        self._infer_w = config.INFERENCE_WIDTH
        self._infer_h = config.INFERENCE_HEIGHT

    def detect(self, frame, timestamp_ms):
        # Downscale for inference; landmarks are normalized to the image used.
        height, width = frame.shape[:2]
        if width != self._infer_w or height != self._infer_h:
            small = cv2.resize(
                frame,
                (self._infer_w, self._infer_h),
                interpolation=cv2.INTER_AREA,
            )
        else:
            small = frame

        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
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

    def handedness_label(self, detection_result, index):
        if not detection_result.handedness:
            return None
        if index >= len(detection_result.handedness):
            return None
        categories = detection_result.handedness[index]
        if not categories:
            return None

        label = categories[0].category_name
        if config.SWAP_HANDEDNESS_FOR_MIRROR:
            if label == "Left":
                return "Right"
            if label == "Right":
                return "Left"
        return label

    def resolve_hands(self, detection_result):
        """Single pass: return (pointer_hand, click_hand)."""
        pointer = None
        click = None

        if not detection_result.hand_landmarks:
            return pointer, click

        pointer_target = config.POINTER_HANDEDNESS.lower()
        click_target = config.CLICK_HANDEDNESS.lower()

        for index, hand in enumerate(detection_result.hand_landmarks):
            label = self.handedness_label(detection_result, index)
            if not label:
                continue
            key = label.lower()
            if pointer is None and key == pointer_target:
                pointer = hand
            elif click is None and key == click_target:
                click = hand

        return pointer, click

    def get_control_point(self, hand):
        if hand is None:
            return None
        return hand[8].x, hand[8].y
