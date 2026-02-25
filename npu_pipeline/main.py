# ============================================================
#  Aura-3D  ·  NPU Pipeline Standalone Demo
#  ──────────────────────────────────────────────────────────
#  Standalone hand tracking + gesture recognition demo.
#  Uses MediaPipe Tasks API (same as aura_npu.py) but runs
#  independently without sending data to Blender.
#
#  Usage:  python npu_pipeline/main.py
# ============================================================

import cv2
import math
import os
import sys
import time

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarkerResult,
    RunningMode,
)
from mediapipe import Image, ImageFormat

# ── Model path ──────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MODEL_PATH = os.path.join(ROOT_DIR, "npu_pipeline", "hand_landmarker.task")


def get_distance(p1, p2):
    """Euclidean distance between two landmarks."""
    return math.sqrt(
        (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2
    )


# ── Shared state for LIVE_STREAM callback ───────────────────
_latest_result: HandLandmarkerResult | None = None


def _on_result(result: HandLandmarkerResult, image: Image, timestamp_ms: int):
    global _latest_result
    _latest_result = result


def classify_gesture(hand_landmarks) -> str:
    """Simple gesture classification from landmarks."""
    thumb_tip = hand_landmarks[4]
    index_tip = hand_landmarks[8]
    middle_tip = hand_landmarks[12]
    ring_tip = hand_landmarks[16]
    pinky_tip = hand_landmarks[20]
    wrist = hand_landmarks[0]
    index_mcp = hand_landmarks[5]

    dist_pinch = get_distance(thumb_tip, index_tip)
    dist_fist = get_distance(index_tip, wrist)

    # Pinch: thumb and index tips are very close
    if dist_pinch < 0.05:
        return "PINCH"

    # Fist: all fingertips are near the base of the hand
    if dist_fist < 0.2:
        return "FIST"

    # Open Palm: fingers extended (index tip above MCP)
    if index_tip.y < index_mcp.y:
        return "OPEN_PALM"

    # Thumbs Up: thumb is extended upward, others curled
    if thumb_tip.y < index_mcp.y and index_tip.y > index_mcp.y:
        return "THUMBS_UP"

    return "MOVE"


def main():
    global _latest_result

    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Hand landmarker model not found at:\n   {MODEL_PATH}")
        return

    # ── Create HandLandmarker ────────────────────────────────
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
        print("❌ Error: Could not open any webcam.")
        return

    print("🚀 Aura-3D Standalone Gesture Demo Active!")
    print("Keep your hand in view of the webcam. Press 'ESC' to exit.")

    frame_ts = 0

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)
            frame_ts += 33
            landmarker.detect_async(mp_image, frame_ts)

            result = _latest_result
            if result and result.hand_landmarks:
                for hand_landmarks in result.hand_landmarks:
                    gesture = classify_gesture(hand_landmarks)

                    # Draw landmarks
                    h, w, _ = frame.shape
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)

                    # Draw connections
                    connections = [
                        (0, 1), (1, 2), (2, 3), (3, 4),
                        (0, 5), (5, 6), (6, 7), (7, 8),
                        (0, 9), (9, 10), (10, 11), (11, 12),
                        (0, 13), (13, 14), (14, 15), (15, 16),
                        (0, 17), (17, 18), (18, 19), (19, 20),
                        (5, 9), (9, 13), (13, 17),
                    ]
                    for start_idx, end_idx in connections:
                        p1 = hand_landmarks[start_idx]
                        p2 = hand_landmarks[end_idx]
                        x1, y1 = int(p1.x * w), int(p1.y * h)
                        x2, y2 = int(p2.x * w), int(p2.y * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)

                    cv2.putText(
                        frame, f"Gesture: {gesture}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2,
                    )

            cv2.imshow("Aura-3D Gesture Demo", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        landmarker.close()
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print("Aura-3D Standalone Demo stopped.")


if __name__ == "__main__":
    main()
