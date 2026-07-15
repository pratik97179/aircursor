import cv2

from hand_tracker import HandTracker


camera = cv2.VideoCapture(0)
tracker = HandTracker()

print("Press 'q' to quit.")

while True:
    success, frame = camera.read()

    if not success:
        break

    # Run hand landmark detection on the current frame.
    result = tracker.detect(frame)

    if result.hand_landmarks:
        # Draw all detected hand landmarks.
        frame = tracker.draw_landmarks(frame, result)

        # Highlight the index fingertip.
        index_tip = tracker.get_index_tip(result)

        height, width, _ = frame.shape

        # Convert normalized landmark coordinates to pixel coordinates.
        x = int(index_tip.x * width)
        y = int(index_tip.y * height)

        cv2.circle(
            frame,
            (x, y),
            10,
            (0, 0, 255),
            -1,
        )

        # Display the fingertip coordinates next to the marker.
        cv2.putText(
            frame,
            f"({x}, {y})",
            (x + 15, y - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

    cv2.imshow("AirCursor", frame)

    # Exit the application when 'q' is pressed.
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
