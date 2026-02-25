# ============================================================
#  Aura-3D  ·  NPU Connector  (Webcam → Blender)
#  ──────────────────────────────────────────────────────────
#  This script bridges the MediaPipe hand-tracking pipeline
#  directly to the Blender Bridge via UDP.
#
#  Uses MediaPipe Tasks API (v0.10.14+) — the new standard.
#
#  Usage:
#    1. Ensure Blender is running with 'Start Bridge' clicked.
#    2. Run this script:  python aura_npu.py
# ============================================================

import cv2
import mediapipe as mp
import socket
import json
import time
import math
import os

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarkerResult,
    RunningMode,
)
from mediapipe import Image, ImageFormat

# ── Configuration ───────────────────────────────────────────
from config import (
    HOST, PORT,
    GESTURE_MOVE, GESTURE_OPEN, GESTURE_PINCH, GESTURE_FIST, GESTURE_PALM
)

# ── Model path ──────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
MODEL_PATH = os.path.join(ROOT_DIR, "npu_pipeline", "hand_landmarker.task")

# ── Network Setup ───────────────────────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def send_gesture(gesture, xyz, confidence=1.0):
    """Sends a JSON packet to the Blender Bridge."""
    payload = {
        "gesture": gesture,
        "xyz": xyz,
        "confidence": confidence,
    }
    data = json.dumps(payload).encode("utf-8")
    sock.sendto(data, (HOST, PORT))


def get_distance(p1, p2):
    """Euclidean distance between two landmarks."""
    return math.sqrt(
        (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2
    )


# ── Shared state for LIVE_STREAM callback ───────────────────
_latest_result: HandLandmarkerResult | None = None


def _on_result(result: HandLandmarkerResult, image: Image, timestamp_ms: int):
    """Called asynchronously by MediaPipe for each processed frame."""
    global _latest_result
    _latest_result = result


def main():
    global _latest_result

    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Hand landmarker model not found at:\n   {MODEL_PATH}")
        print("   Download it with:")
        print("   python -c \"import urllib.request; urllib.request.urlretrieve("
              "'https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
              "hand_landmarker/float16/latest/hand_landmarker.task', "
              "'npu_pipeline/hand_landmarker.task')\"")
        time.sleep(5)
        return

    # ── Create HandLandmarker in LIVE_STREAM mode ────────────
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.LIVE_STREAM,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        result_callback=_on_result,
    )

    landmarker = HandLandmarker.create_from_options(options)

    # ── Open webcam ──────────────────────────────────────────
    cap = None
    for index in range(3):
        print(f"[Aura] Checking camera index {index}...")
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            print(f"[Aura] ✔ Camera found at index {index}")
            break
        if cap:
            cap.release()
        cap = None

    if cap is None:
        print("❌ Error: Could not open any webcam. Please check your connection.")
        time.sleep(5)
        return

    print(f"🚀 Aura-3D NPU Bridge Active!")
    print(f"Targeting Blender at {HOST}:{PORT}")
    print("Keep your hand in view of the webcam. Press 'ESC' to exit.")

    frame_ts = 0

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("⚠ Warning: Failed to grab frame.")
                break

            # Flip for mirror effect and convert to RGB
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to MediaPipe Image and detect asynchronously
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)
            frame_ts += 33  # ~30 fps timestamps in ms
            landmarker.detect_async(mp_image, frame_ts)

            # Process latest result (from callback)
            result = _latest_result
            if result and result.hand_landmarks:
                for hand_landmarks in result.hand_landmarks:
                    # 1. Get Hand Center (Landmark 9: Middle Finger MCP)
                    center = hand_landmarks[9]

                    # 2. Gesture Logic
                    thumb_tip = hand_landmarks[4]
                    index_tip = hand_landmarks[8]
                    pinky_tip = hand_landmarks[20]

                    dist_pinch = get_distance(thumb_tip, index_tip)
                    dist_fist = get_distance(
                        index_tip, hand_landmarks[0]
                    )  # distance to wrist

                    # Heuristics for gestures
                    gesture = GESTURE_MOVE

                    # Pinch: Tips are very close
                    if dist_pinch < 0.05:
                        gesture = GESTURE_PINCH
                    # Fist: Index tip is near the base of the hand
                    elif dist_fist < 0.2:
                        gesture = GESTURE_FIST
                    # Palm: Open hand (index finger extended upward)
                    elif index_tip.y < hand_landmarks[5].y:
                        gesture = GESTURE_PALM

                    # 3. Map coordinates for Blender
                    xyz = [
                        center.x,
                        1.0 - center.y,  # Flip Y for Blender world space
                        center.z,
                    ]

                    # 4. SEND TO BLENDER
                    send_gesture(gesture, xyz)

                    # Draw landmarks on frame for visual feedback
                    h, w, _ = frame.shape
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)

                    # Draw connections (simplified)
                    connections = [
                        (0, 1), (1, 2), (2, 3), (3, 4),    # Thumb
                        (0, 5), (5, 6), (6, 7), (7, 8),    # Index
                        (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
                        (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
                        (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
                        (5, 9), (9, 13), (13, 17),            # Palm
                    ]
                    for start_idx, end_idx in connections:
                        p1 = hand_landmarks[start_idx]
                        p2 = hand_landmarks[end_idx]
                        x1, y1 = int(p1.x * w), int(p1.y * h)
                        x2, y2 = int(p2.x * w), int(p2.y * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)

                    cv2.putText(
                        frame,
                        f"Gesture: {gesture}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

            # Show the feed
            cv2.imshow("Aura-3D NPU Monitor", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    except Exception as e:
        print(f"❌ NPU Error: {str(e)}")
        import traceback
        traceback.print_exc()
        time.sleep(5)
    finally:
        landmarker.close()
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print("Aura-3D NPU Bridge stopped.")


if __name__ == "__main__":
    main()
