import cv2

# Open the default webcam (0 = built-in camera)
camera = cv2.VideoCapture(0)

# Check if the webcam opened successfully
if not camera.isOpened():
    print("Failed to open webcam.")
    exit()

print("Press 'q' to quit.")

while True:
    # Read a frame from the webcam
    success, frame = camera.read()

    if not success:
        print("Failed to capture frame.")
        break

    # Display the frame
    cv2.imshow("AirCursor", frame)

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release resources
camera.release()
cv2.destroyAllWindows()
