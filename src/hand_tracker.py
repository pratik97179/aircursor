"""MediaPipe hand landmark adapter. No interaction state."""

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Lock, Thread

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import config

# MediaPipe hand connections (wrist → tips) for skeleton draw.
_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
)


@dataclass(frozen=True)
class _EmptyDetectionResult:
    hand_landmarks: tuple = ()
    handedness: tuple = ()


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
        self._result_lock = Lock()
        self._latest_result = _EmptyDetectionResult()
        self._inference_queue = Queue(maxsize=1)
        self._closed = False

        base_options = python.BaseOptions(
            model_asset_path=str(model_path),
            delegate=python.BaseOptions.Delegate.CPU,
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=config.NUM_HANDS,
            min_hand_detection_confidence=config.MIN_HAND_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_HAND_PRESENCE_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
        )

        self.detector = vision.HandLandmarker.create_from_options(options)
        self._infer_w = config.INFERENCE_WIDTH
        self._infer_h = config.INFERENCE_HEIGHT
        self._prev_pointer = None
        self._prev_click = None
        self._worker = Thread(
            target=self._inference_loop,
            name="aircursor-hand-inference",
            daemon=True,
        )
        self._worker.start()

    def _inference_loop(self):
        while True:
            item = self._inference_queue.get()
            if item is None:
                return
            rgb, timestamp_ms = item
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect_for_video(image, timestamp_ms)
            with self._result_lock:
                self._latest_result = result

    def detect(self, frame, timestamp_ms):
        """Queue the latest frame and return the last completed result.

        The one-slot worker queue drops stale frames while preserving VIDEO
        mode, so MediaPipe never blocks the camera/UI thread.
        """
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
        item = (rgb, int(timestamp_ms))
        try:
            self._inference_queue.put_nowait(item)
        except Full:
            # Replace queued-but-not-started work with the newest camera frame.
            try:
                self._inference_queue.get_nowait()
            except Empty:
                pass
            try:
                self._inference_queue.put_nowait(item)
            except Full:
                pass

        with self._result_lock:
            return self._latest_result

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._inference_queue.get_nowait()
        except Empty:
            pass
        self._inference_queue.put(None)
        self._worker.join()
        self.detector.close()

    def draw_landmarks(self, frame, detection_result):
        """Draw MediaPipe-style skeleton (connections + joints)."""
        height, width, _ = frame.shape

        for hand in detection_result.hand_landmarks:
            pts = []
            for landmark in hand:
                pts.append((int(landmark.x * width), int(landmark.y * height)))

            for a, b in _HAND_CONNECTIONS:
                cv2.line(frame, pts[a], pts[b], (80, 200, 80), 2, cv2.LINE_AA)

            for x, y in pts:
                cv2.circle(frame, (x, y), 4, (0, 255, 0), -1, cv2.LINE_AA)

        return frame

    def handedness_label(self, detection_result, index):
        """Return (label, score) with mirror swap; None if missing/low score."""
        if not detection_result.handedness:
            return None, 0.0
        if index >= len(detection_result.handedness):
            return None, 0.0
        categories = detection_result.handedness[index]
        if not categories:
            return None, 0.0

        category = categories[0]
        label = category.category_name
        score = float(getattr(category, "score", 0.0) or 0.0)

        if score < config.HANDEDNESS_MIN_SCORE:
            return None, score

        if config.SWAP_HANDEDNESS_FOR_MIRROR:
            if label == "Left":
                label = "Right"
            elif label == "Right":
                label = "Left"
        return label, score

    def resolve_hands(self, detection_result):
        """Single pass: return (pointer_hand, click_hand).

        Low-confidence handedness keeps the previous frame's assignment for
        that role when the same hand count is present.
        """
        pointer = None
        click = None

        if not detection_result.hand_landmarks:
            self._prev_pointer = None
            self._prev_click = None
            return pointer, click

        pointer_target = config.POINTER_HANDEDNESS.lower()
        click_target = config.CLICK_HANDEDNESS.lower()
        uncertain = []

        for index, hand in enumerate(detection_result.hand_landmarks):
            label, _score = self.handedness_label(detection_result, index)
            if not label:
                uncertain.append(hand)
                continue
            key = label.lower()
            if pointer is None and key == pointer_target:
                pointer = hand
            elif click is None and key == click_target:
                click = hand

        # Fill gaps from previous frame when handedness was uncertain.
        if pointer is None and self._prev_pointer is not None and uncertain:
            pointer = uncertain.pop(0)
        if click is None and self._prev_click is not None and uncertain:
            click = uncertain.pop(0)

        # If still missing and only one confident hand, don't invent roles.
        self._prev_pointer = pointer
        self._prev_click = click
        return pointer, click

    def get_control_point(self, hand):
        if hand is None:
            return None
        return hand[8].x, hand[8].y
