import time

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import pyttsx3

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)    # Speed of speech
tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

screen_w, screen_h = pyautogui.size()

prev_x, prev_y = 0, 0
smoothening = 6

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

BLINK_THRESHOLD = 0.20        # EAR below this = eye closed
long_closure_start = 0
long_closure_triggered = False
LONG_CLOSURE_DURATION = 2.0   # seconds to trigger a long‑closure click
LONG_CLOSURE_ACTION = pyautogui.leftClick   # function (no parentheses)

state = 'idle'
start_countdown_end = 0

nod_count = 0
nod_state = 'up'               # 'up' or 'down'
nod_start_time = 0
NOD_THRESHOLD = 15             # vertical movement (pixels) to count as nod
NOD_TIMEOUT = 3.0              # seconds to complete 3 nods

lr_state = 'neutral'           # 'neutral', 'left', 'right'
lr_count = 0
lr_start_time = 0
LR_THRESHOLD = 20              # horizontal movement (pixels)
LR_TIMEOUT = 3.0               # seconds to complete pattern

window_name = "Face Mouse Control"
cv2.namedWindow(window_name)
VIDEO_WIDTH, VIDEO_HEIGHT = 640, 480
VIDEO_X, VIDEO_Y = 20, 20

BUTTON_WIDTH, BUTTON_HEIGHT = 150, 50
START_BTN = (700, 50, 850, 100)
STOP_BTN  = (700, 120, 850, 170)
CLOSE_BTN = (700, 190, 850, 240)

exit_app = False   # when True, program will close

def eye_aspect_ratio(landmarks, eye_points, frame_w, frame_h):
    points = []
    for p in eye_points:
        x = int(landmarks[p].x * frame_w)
        y = int(landmarks[p].y * frame_h)
        points.append((x, y))
    v1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
    v2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
    h  = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
    ear = (v1 + v2) / (2.0 * h)
    return ear

def mouse_callback(event, x, y, flags, param):
    global state, start_countdown_end, exit_app
    if event == cv2.EVENT_LBUTTONDOWN:
        # Start button
        if (START_BTN[0] <= x <= START_BTN[2] and
            START_BTN[1] <= y <= START_BTN[3]):
            if state != 'active':
                state = 'active'
                print("Started by button")
        # Stop button
        if (STOP_BTN[0] <= x <= STOP_BTN[2] and
            STOP_BTN[1] <= y <= STOP_BTN[3]):
            if state != 'idle':
                state = 'idle'
                print("Stopped by button")
        # Close button
        if (CLOSE_BTN[0] <= x <= CLOSE_BTN[2] and
            CLOSE_BTN[1] <= y <= CLOSE_BTN[3]):
            exit_app = True
            print("Exit requested")

cv2.setMouseCallback(window_name, mouse_callback)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    frame_h, frame_w, _ = frame.shape

    # Create blank canvas for GUI
    canvas = np.ones((600, 1000, 3), dtype=np.uint8) * 255  # white background

    # Place video feed
    video_frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
    canvas[VIDEO_Y:VIDEO_Y+VIDEO_HEIGHT, VIDEO_X:VIDEO_X+VIDEO_WIDTH] = video_frame

    # Draw buttons
    # Start
    cv2.rectangle(canvas, (START_BTN[0], START_BTN[1]),
                  (START_BTN[2], START_BTN[3]), (0, 200, 0), -1)
    cv2.putText(canvas, "START", (START_BTN[0]+30, START_BTN[1]+35),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    # Stop
    cv2.rectangle(canvas, (STOP_BTN[0], STOP_BTN[1]),
                  (STOP_BTN[2], STOP_BTN[3]), (0, 0, 200), -1)
    cv2.putText(canvas, "STOP", (STOP_BTN[0]+35, STOP_BTN[1]+35),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    # Exit
    cv2.rectangle(canvas, (CLOSE_BTN[0], CLOSE_BTN[1]),
                  (CLOSE_BTN[2], CLOSE_BTN[3]), (100, 100, 100), -1)
    cv2.putText(canvas, "EXIT", (CLOSE_BTN[0]+35, CLOSE_BTN[1]+35),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    # Instructions
    y0 = 250
    cv2.putText(canvas, "How to use:", (700, y0), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0,0,0), 2)
    instructions = [
        "1. Click START or nod 3 times to begin",
        "2. Move head to move cursor",
        "3. Close eyes for 2 seconds to click",
        "4. You will hear 'button clicked' when action is performed",
        "5. To stop: click STOP or move head left-right-left",
        "6. Click EXIT to close"
    ]
    for i, line in enumerate(instructions):
        y = y0 + 30 + i*25
        cv2.putText(canvas, line, (700, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (50,50,50), 1)

    # Status display
    if state == 'active':
        cv2.putText(canvas, "STATUS: ACTIVE", (700, 400),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,150,0), 2)
    elif state == 'starting':
        remaining = max(0, int(start_countdown_end - time.time()))
        cv2.putText(canvas, f"STATUS: STARTING in {remaining}s", (700, 400),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,100,0), 2)
    else:
        cv2.putText(canvas, "STATUS: IDLE", (700, 400),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150,0,0), 2)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            landmarks = face_landmarks.landmark

            # Nose tip for movement & gestures
            nose = landmarks[1]
            nose_x = int(nose.x * frame_w)
            nose_y = int(nose.y * frame_h)

            current_time = time.time()

            if state == 'idle':
                if 'prev_nose_y' not in locals():
                    prev_nose_y = nose_y

                diff_y = nose_y - prev_nose_y   # positive = down

                if nod_state == 'up' and diff_y > NOD_THRESHOLD:
                    nod_state = 'down'
                    nod_start_time = current_time
                elif nod_state == 'down' and diff_y < -NOD_THRESHOLD:
                    nod_count += 1
                    nod_state = 'up'
                    nod_start_time = current_time

                # Timeout
                if current_time - nod_start_time > NOD_TIMEOUT:
                    nod_count = 0
                    nod_state = 'up'

                if nod_count >= 3:
                    state = 'starting'
                    start_countdown_end = current_time + 5
                    nod_count = 0
                    nod_state = 'up'
                    print("Nod detected: starting in 5 seconds")

                prev_nose_y = nose_y

            if state == 'active':
                if 'prev_nose_x' not in locals():
                    prev_nose_x = nose_x

                diff_x = nose_x - prev_nose_x   # positive = right

                if lr_state == 'neutral':
                    if diff_x < -LR_THRESHOLD:
                        lr_state = 'left'
                        lr_count = 1
                        lr_start_time = current_time
                    elif diff_x > LR_THRESHOLD:
                        lr_state = 'right'
                        lr_count = 1
                        lr_start_time = current_time
                elif lr_state == 'left':
                    if diff_x > LR_THRESHOLD:
                        lr_state = 'right'
                        lr_count = 2
                        lr_start_time = current_time
                elif lr_state == 'right':
                    if diff_x < -LR_THRESHOLD:
                        lr_state = 'left'
                        lr_count = 3
                        lr_start_time = current_time

                if lr_count == 3:
                    state = 'idle'
                    print("Left‑right‑left detected: stopped")
                    lr_count = 0
                    lr_state = 'neutral'

                if current_time - lr_start_time > LR_TIMEOUT:
                    lr_count = 0
                    lr_state = 'neutral'

                prev_nose_x = nose_x

            if state == 'active':
                # ---- Mouse movement ----
                screen_x = np.interp(nose_x, [100, frame_w-100], [0, screen_w])
                screen_y = np.interp(nose_y, [100, frame_h-100], [0, screen_h])

                curr_x = prev_x + (screen_x - prev_x) / smoothening
                curr_y = prev_y + (screen_y - prev_y) / smoothening

                pyautogui.moveTo(curr_x, curr_y)
                prev_x, prev_y = curr_x, curr_y

                # ---- Eye state detection (both eyes) ----
                ear_left = eye_aspect_ratio(landmarks, LEFT_EYE, frame_w, frame_h)
                ear_right = eye_aspect_ratio(landmarks, RIGHT_EYE, frame_w, frame_h)
                ear = (ear_left + ear_right) / 2.0

                # ---- Long‑closure detection (eyes kept closed) ----
                if ear < BLINK_THRESHOLD:   # eyes closed
                    if long_closure_start == 0:
                        long_closure_start = time.time()
                        long_closure_triggered = False
                    else:
                        # If eyes remain closed beyond LONG_CLOSURE_DURATION, trigger action once
                        if not long_closure_triggered and (time.time() - long_closure_start) >= LONG_CLOSURE_DURATION:
                            print("Long closure detected: performing click")
                            LONG_CLOSURE_ACTION()   # e.g., left click
                            # Speak feedback
                            tts_engine.say("button clicked")
                            tts_engine.runAndWait()
                            long_closure_triggered = True
                else:                         # eyes open
                    long_closure_start = 0
                    long_closure_triggered = False

    if state == 'starting' and time.time() >= start_countdown_end:
        state = 'active'
        print("Countdown finished: now active")

    if exit_app:
        break

    cv2.imshow(window_name, canvas)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()