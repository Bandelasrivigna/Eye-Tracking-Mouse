# Hands-Free Mouse Control System

Full computer control from a standard webcam, for people who cannot use a mouse or keyboard. Move the cursor with your nose, click by closing your eyes, and call for help without touching anything.

Commercial eye-tracking and head-tracking hardware runs $500 to $5,000. This runs on the webcam already in the laptop.

---

## What it does

| You do this | It does this |
|---|---|
| Move your nose | Cursor follows, like a laser pointer |
| Close both eyes for 2 seconds | Left click, with an on-screen progress bar |
| Nod three times, or show an open hand | Start tracking |
| Turn head left → right → left, or make a fist | Stop tracking |
| Show both hands, fully open | Opens the on-screen keyboard |
| Hover a quick action and close your eyes | Speaks the phrase aloud three times |
| Trigger Emergency | Emails a caregiver with the activity log attached |

**Quick actions:** Hungry · Thirsty · Help · Emergency · Take me out · Water · Bathroom · Pain · I need attention

Every action is timestamped and written to an Excel log, which gives a caregiver a record of what happened and when.

---

## How it works

```
Webcam → MediaPipe (face mesh + hand landmarks) → gesture recognition → action
```

Two processes, deliberately separated:

- **`controller.py`** — computer vision and gesture detection, running on a background daemon thread so the interface never freezes waiting on a frame
- **`Eyetrack.py`** — the Tkinter interface, live video preview, sensitivity controls and Excel logging

The controller runs a three-state machine: `IDLE → STARTING (5s countdown) → ACTIVE`. Nothing moves the real cursor until it reaches ACTIVE, so a user who is still getting settled does not fight a cursor that has already started following them.

### Cursor movement

The nose tip (face landmark 1) is mapped from camera space to screen space with `np.interp`, inset by a 30px margin so the edges of the screen stay reachable without pressing your face against the edge of frame.

Raw landmark positions jitter. Each new position is blended with the previous one rather than jumping to it:

```python
cx = self.prev_x + (sx - self.prev_x) / self.smooth_factor
```

The smoothing factor is exposed as a slider, because the right amount of damping is different for someone with a tremor than for someone without one.

### Click detection

Blink detection uses the **Eye Aspect Ratio**, computed over six landmarks per eye:

```
EAR = (vertical distance 1 + vertical distance 2) / (2 × horizontal distance)
```

EAR collapses toward zero when the eyelid closes and is largely independent of how far the user sits from the camera, which a raw pixel distance would not be.

A blink is not a click. The threshold fires at EAR < 0.20, but the click only triggers after the eyes have stayed closed for a **full 2 seconds**, and the progress bar fills during that window so the user can abort by opening their eyes. This is what keeps normal blinking from clicking things at random.

### Gesture detection

- **Nod:** vertical nose displacement past 15px, tracked through an up/down state machine, three cycles inside a 3-second window
- **Left-right-left:** horizontal displacement past 20px, same state machine approach, 3-second window
- **Finger counting:** fingertip landmarks compared against their PIP joints — vertically for the four fingers, horizontally for the thumb, with the comparison direction flipped depending on which hand MediaPipe reports

Both directional gestures reset on timeout, so a slow head turn during normal use never accumulates into a stop command.

### Speech

Text-to-speech runs in its own thread with a fresh `pyttsx3` engine per utterance. Doing it inline blocks the video loop, which stalls the cursor mid-sentence.

---

## Results

Measured over 50 trials per gesture on Windows 11, Intel i5, 8GB RAM, 30fps webcam:

| Gesture | Success rate |
|---|---|
| Nose cursor tracking | 100% responsiveness |
| Quick action trigger | 96% |
| Nod to start | 94% |
| Eye closure click | 92% |
| Hand gestures | 88% (lighting dependent) |

End-to-end latency from gesture to action stays under 100ms.

---

## Setup

Requires Python 3.8+ and a webcam.

```bash
git clone https://github.com/Bandelasrivigna/Eye-Tracking-Mouse.git
cd Eye-Tracking-Mouse
pip install -r requirements.txt
```

### Email alerts

The emergency feature sends mail through Gmail SMTP, which needs an **app password**, not your normal account password. Generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (2-Step Verification must be on first).

Open `email_sender.py` and `testmail.py` and replace `PUT_APP_PASSWORD_HERE` with it, along with the sender and recipient addresses.

Verify it works before relying on it:

```bash
python testmail.py
```

### Run

```bash
python Eyetrack.py
```

Click **Start**, or nod three times. The status panel shows IDLE, STARTING or ACTIVE.

---

## Limitations

Worth knowing before you rely on this:

- Hand gesture detection degrades in poor lighting
- Sustained eye closure is difficult for some users, which is exactly the population this targets — the duration is adjustable, but it remains a real barrier for some
- Sensitivity currently needs manual tuning per user; there is no calibration wizard
- Head movement is required, so users who cannot move their head are not yet served. True gaze tracking would address this and is the most valuable thing left to build.

## Planned

- Gaze tracking for users without head mobility
- Calibration wizard that learns each user's comfortable range of motion
- Voice command input
- Web dashboard so caregivers can see logs live rather than by email attachment

---

## Built with

`opencv-python` · `mediapipe` · `pyautogui` · `pyttsx3` · `openpyxl` · `Pillow` · `numpy` · `tkinter` · `python-pptx`

## Team

Ram Chandhar Muddam · Srivigna Bandela · Naga Ashrith Vollala · Sukrutha Budda · Yashas Chandra Pendem

Data Science project, April 2026.
