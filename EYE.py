import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time

# Screen size
screen_w, screen_h = pyautogui.size()

# Mediapipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Start webcam
cap = cv2.VideoCapture(0)

# Mouse smoothing
prev_x, prev_y = 0, 0
smoothening = 7

# Blink detection variables
blink_start = 0
blink_count = 0
last_blink_time = 0

# Eye landmarks
LEFT_EYE = [33, 160, 158, 133, 153, 144]


def eye_aspect_ratio(landmarks, eye_points, frame_w, frame_h):
    points = []

    for p in eye_points:
        x = int(landmarks[p].x * frame_w)
        y = int(landmarks[p].y * frame_h)
        points.append((x, y))

    v1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
    v2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
    h = np.linalg.norm(np.array(points[0]) - np.array(points[3]))

    ear = (v1 + v2) / (2.0 * h)

    return ear


while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera not detected")
        break

    frame = cv2.flip(frame, 1)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_mesh.process(rgb_frame)

    frame_h, frame_w, _ = frame.shape

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            landmarks = face_landmarks.landmark

            # Nose used for cursor movement
            nose = landmarks[1]

            x = int(nose.x * frame_w)
            y = int(nose.y * frame_h)

            # Map face position to screen
            screen_x = np.interp(x, [100, frame_w - 100], [0, screen_w])
            screen_y = np.interp(y, [100, frame_h - 100], [0, screen_h])

            # Smooth cursor movement
            curr_x = prev_x + (screen_x - prev_x) / smoothening
            curr_y = prev_y + (screen_y - prev_y) / smoothening

            pyautogui.moveTo(curr_x, curr_y)

            prev_x, prev_y = curr_x, curr_y

            # Blink detection
            ear = eye_aspect_ratio(landmarks, LEFT_EYE, frame_w, frame_h)

            if ear < 0.20:
                if blink_start == 0:
                    blink_start = time.time()

            else:
                if blink_start != 0:

                    blink_duration = time.time() - blink_start
                    blink_start = 0

                    if blink_duration < 0.4:
                        blink_count += 1
                        last_blink_time = time.time()

            # Click logic
            if blink_count == 1 and time.time() - last_blink_time > 0.7:
                print("Right Click")
                pyautogui.rightClick()
                blink_count = 0

            elif blink_count >= 2:
                print("Left Click")
                pyautogui.leftClick()
                blink_count = 0

    cv2.imshow("AI Face Mouse", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()