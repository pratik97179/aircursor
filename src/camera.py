"""Webcam capture. No computer-vision logic."""

import cv2

import config


class Camera:

    def __init__(
        self,
        index=None,
        width=None,
        height=None,
    ):
        index = config.CAMERA_INDEX if index is None else index
        width = config.CAMERA_WIDTH if width is None else width
        height = config.CAMERA_HEIGHT if height is None else height

        self._capture = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self):
        success, frame = self._capture.read()
        if not success or frame is None:
            return None
        return cv2.flip(frame, 1)

    def release(self):
        self._capture.release()
