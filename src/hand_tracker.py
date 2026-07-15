import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class HandTracker:
    def __init__(self):
        # Load the pre-trained hand landmark detection model.
        base_options = python.BaseOptions(
            model_asset_path="models/hand_landmarker.task"
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
        )

        self.detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame):
        # MediaPipe expects RGB images, while OpenCV captures frames in BGR.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        return self.detector.detect(image)

    def draw_landmarks(self, frame, detection_result):
        """Draw all detected hand landmarks on the frame."""

        height, width, _ = frame.shape

        for hand in detection_result.hand_landmarks:
            for landmark in hand:
                # Convert normalized coordinates (0.0 - 1.0) to image pixels.
                x = int(landmark.x * width)
                y = int(landmark.y * height)

                cv2.circle(
                    frame,
                    (x, y),
                    5,
                    (0, 255, 0),
                    -1,
                )

        return frame

    def get_index_tip(self, detection_result):
        """Return the index fingertip landmark of the first detected hand."""

        if not detection_result.hand_landmarks:
            return None

        # Landmark 8 always represents the index fingertip.
        return detection_result.hand_landmarks[0][8]
