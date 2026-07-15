import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class HandTracker:

    def __init__(self):

        base_options = python.BaseOptions(
            model_asset_path="models/hand_landmarker.task"
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
        )

        self.detector = vision.HandLandmarker.create_from_options(
            options
        )

    def detect(self, frame):

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        return self.detector.detect(image)

    def draw_landmarks(self, frame, detection_result):

        height, width, _ = frame.shape

        for hand in detection_result.hand_landmarks:

            for landmark in hand:

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

    def get_control_point(self, detection_result):

        if not detection_result.hand_landmarks:
            return None

        hand = detection_result.hand_landmarks[0]

        # Index fingertip (Landmark 8)
        return hand[8].x, hand[8].y
