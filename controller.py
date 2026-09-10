import platform
import subprocess
import threading
import time

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import pyttsx3

from email_sender import send_emergency_email


class FaceHandController:
    def __init__(self, callback=None, on_long_click=None):
        self.callback = callback
        self.on_long_click = on_long_click
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # MediaPipe models
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7,
                                         min_tracking_confidence=0.5)
        self.mp_draw = mp.solutions.drawing_utils

        # Screen size
        self.screen_w, self.screen_h = pyautogui.size()

        # Mouse smoothing
        self.prev_x, self.prev_y = 0, 0
        self.smooth_factor = 2
        self.margin = 30

        # Eye landmarks
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.BLINK_THRESHOLD = 0.20

        # Long‑closure click
        self.long_closure_start = 0
        self.long_closure_triggered = False
        self.LONG_CLOSURE_DURATION = 2.0
        self.LONG_CLOSURE_ACTION = pyautogui.leftClick

        # Gesture variables
        self.state = 'idle'
        self.start_countdown_end = 0
        self.nod_count = 0
        self.nod_state = 'up'
        self.nod_start_time = 0
        self.NOD_THRESHOLD = 15
        self.NOD_TIMEOUT = 3.0
        self.lr_state = 'neutral'
        self.lr_count = 0
        self.lr_start_time = 0
        self.LR_THRESHOLD = 20
        self.LR_TIMEOUT = 3.0

        self.frame_w = 640
        self.frame_h = 480

    def eye_aspect_ratio(self, landmarks, eye_points):
        points = []
        for p in eye_points:
            x = int(landmarks[p].x * self.frame_w)
            y = int(landmarks[p].y * self.frame_h)
            points.append((x, y))
        v1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
        v2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
        h = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
        return (v1 + v2) / (2.0 * h)

    def count_fingers(self, hand_landmarks, handedness):
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        count = 0
        for i in range(5):
            tip = hand_landmarks.landmark[tips[i]]
            pip = hand_landmarks.landmark[pips[i]]
            if i == 0:
                if handedness == 'Right':
                    if tip.x > pip.x: count += 1
                else:
                    if tip.x < pip.x: count += 1
            else:
                if tip.y < pip.y: count += 1
        return count

    def open_keyboard(self):
        system = platform.system()
        try:
            if system == 'Windows':
                subprocess.Popen('osk', shell=True)
            elif system == 'Linux':
                try:
                    subprocess.Popen(['onboard'])
                except FileNotFoundError:
                    subprocess.Popen(['florence'])
            else:
                self.speak_repeated("Keyboard not available", 1)
                return
            self.speak_repeated("Opening keyboard", 1)
        except Exception as e:
            print(f"Error opening keyboard: {e}")

    def speak_repeated(self, phrase, times=1):
        """Thread-safe speech function"""
        def speech_worker():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                for _ in range(times):
                    engine.say(phrase)
                    engine.runAndWait()
                # Stop engine properly
                engine.stop()
            except Exception as e:
                print(f"Speech Thread Error: {e}")
        
        threading.Thread(target=speech_worker, daemon=True).start()

    def send_emergency_email(self):
        success, msg = send_emergency_email()
        if success:
            self.speak_repeated("Emergency email sent", 1)
        else:
            self.speak_repeated("Email failed", 1)
        return success

    def _process(self):
        cap = cv2.VideoCapture(0)
        while self.running:
            ret, frame = cap.read()
            if not ret: continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = self.face_mesh.process(rgb)
            hand_results = self.hands.process(rgb)
            self.frame_h, self.frame_w, _ = frame.shape
            nose_x, nose_y = 0, 0

            # Hand detection
            self.both_hands_open = False
            if hand_results.multi_hand_landmarks:
                open_hands = 0
                for idx, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
                    handedness = hand_results.multi_handedness[idx].classification[0].label
                    if self.count_fingers(hand_landmarks, handedness) >= 4:
                        open_hands += 1
                self.both_hands_open = (open_hands == 2)
                self.hand_open = (open_hands >= 1)
                self.hand_closed = (open_hands == 0)
            else:
                self.hand_open = self.hand_closed = self.both_hands_open = False

            if self.both_hands_open:
                if not hasattr(self, '_kb_trig'): self._kb_trig = False
                if not self._kb_trig:
                    self.open_keyboard()
                    self._kb_trig = True
            else: self._kb_trig = False

            # Face processing
            if face_results.multi_face_landmarks:
                for face_landmarks in face_results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark
                    nose = landmarks[1]
                    nose_x, nose_y = int(nose.x * self.frame_w), int(nose.y * self.frame_h)
                    self.mp_draw.draw_landmarks(frame, face_landmarks, self.mp_face_mesh.FACEMESH_CONTOURS)
                    now = time.time()

                    if self.state == 'idle':
                        if 'p_ny' not in locals(): p_ny = nose_y
                        if self.nod_state == 'up' and (nose_y - p_ny) > self.NOD_THRESHOLD:
                            self.nod_state = 'down'; self.nod_start_time = now
                        elif self.nod_state == 'down' and (nose_y - p_ny) < -self.NOD_THRESHOLD:
                            self.nod_count += 1; self.nod_state = 'up'; self.nod_start_time = now
                        if now - self.nod_start_time > self.NOD_TIMEOUT: self.nod_count = 0
                        if self.nod_count >= 3:
                            self.state = 'starting'; self.start_countdown_end = now + 5
                            self.speak_repeated("Starting in 5 seconds", 1)
                        p_ny = nose_y
                        if self.hand_open:
                            self.state = 'active'; self.speak_repeated("Started", 1)

                    elif self.state == 'starting':
                        if now >= self.start_countdown_end:
                            self.state = 'active'; self.speak_repeated("Active", 1)

                    elif self.state == 'active':
                        # Mouse logic
                        sx = np.interp(nose_x, [self.margin, self.frame_w-self.margin], [0, self.screen_w])
                        sy = np.interp(nose_y, [self.margin, self.frame_h-self.margin], [0, self.screen_h])
                        cx = self.prev_x + (sx - self.prev_x) / self.smooth_factor
                        cy = self.prev_y + (sy - self.prev_y) / self.smooth_factor
                        pyautogui.moveTo(cx, cy); self.prev_x, self.prev_y = cx, cy

                        # Eye click logic
                        ear = (self.eye_aspect_ratio(landmarks, self.LEFT_EYE) + self.eye_aspect_ratio(landmarks, self.RIGHT_EYE)) / 2.0
                        if ear < self.BLINK_THRESHOLD:
                            if self.long_closure_start == 0: self.long_closure_start = now
                            elapsed = now - self.long_closure_start
                            # Progress bar
                            p = min(elapsed / self.LONG_CLOSURE_DURATION, 1.0)
                            cv2.rectangle(frame, (50, 430), (350, 450), (200,200,200), 2)
                            cv2.rectangle(frame, (50, 430), (50+int(300*p), 450), (0,255,0), -1)
                            if not self.long_closure_triggered and elapsed >= self.LONG_CLOSURE_DURATION:
                                x, y = pyautogui.position()
                                if self.on_long_click and self.on_long_click(x, y): pass
                                else: 
                                    pyautogui.click()
                                    self.speak_repeated("Clicked", 1)
                                self.long_closure_triggered = True
                        else: self.long_closure_start = 0; self.long_closure_triggered = False

                        # Stop gesture (Left-Right-Left)
                        if 'p_nx' not in locals(): p_nx = nose_x
                        dx = nose_x - p_nx
                        if self.lr_state == 'neutral' and abs(dx) > self.LR_THRESHOLD:
                            self.lr_state = 'left' if dx < 0 else 'right'
                            self.lr_count = 1; self.lr_start_time = now
                        elif (self.lr_state == 'left' and dx > self.LR_THRESHOLD) or (self.lr_state == 'right' and dx < -self.LR_THRESHOLD):
                            self.lr_count += 1; self.lr_state = 'right' if dx > 0 else 'left'
                            self.lr_start_time = now
                        if self.lr_count >= 3:
                            self.state = 'idle'; self.speak_repeated("Stopped", 1)
                            self.lr_count = 0; self.lr_state = 'neutral'
                        if now - self.lr_start_time > self.LR_TIMEOUT: self.lr_count = 0; self.lr_state = 'neutral'
                        p_nx = nose_x
                        if self.hand_closed: self.state = 'idle'; self.speak_repeated("Stopped", 1)

            status_text = "ACTIVE" if self.state == 'active' else f"STARTING {int(max(0, self.start_countdown_end-time.time()))}s" if self.state == 'starting' else "IDLE"
            if self.callback: self.callback(frame, status_text)
        cap.release()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._process, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1.0)