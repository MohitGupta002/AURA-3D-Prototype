# ============================================================
#  Aura-3D  ·  NPU Connector  (Webcam -> Blender)
#  Uses MediaPipe Tasks API + OpenCV Contour Analysis
# ============================================================

import cv2
import mediapipe as mp
import socket
import json
import time
import math
import os
import sys
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker, HandLandmarkerOptions, HandLandmarkerResult, RunningMode,
)
from mediapipe import Image, ImageFormat

from config import (
    HOST, PORT,
    GESTURE_MOVE, GESTURE_OPEN, GESTURE_PINCH, GESTURE_FIST, GESTURE_PALM
)

ROOT_DIR   = os.path.dirname(os.path.realpath(__file__))
MODEL_PATH = os.path.join(ROOT_DIR, "npu_pipeline", "hand_landmarker.task")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

PINCH_START_THRESH = 0.045
PINCH_END_THRESH   = 0.085
MIN_DRAW_POINTS    = 10
MIN_DRAW_TIME      = 0.8


def send_gesture(gesture, xyz, confidence=1.0):
    payload = {"gesture": gesture, "xyz": xyz, "confidence": confidence}
    sock.sendto(json.dumps(payload).encode("utf-8"), (HOST, PORT))


def send_draw_2d(shape, center, size):
    payload = {"action": "DRAW_2D", "shape": shape, "center": center, "size": size}
    sock.sendto(json.dumps(payload).encode("utf-8"), (HOST, PORT))
    print(f"[Aura-3D] Sent DRAW_2D -> {shape}")


def send_erase():
    payload = {"action": "ERASE"}
    sock.sendto(json.dumps(payload).encode("utf-8"), (HOST, PORT))
    print("[Aura-3D] Sent ERASE")


def get_distance(p1, p2):
    return math.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2 + (p1.z-p2.z)**2)


# ═════════════════════════════════════════════════════════════
#  SHAPE CLASSIFIER v8 — Vertex-First Decision Tree
# ═════════════════════════════════════════════════════════════
# Three-stage pipeline:
#   1. SMOOTH: Moving-average filter removes hand jitter
#   2. RESAMPLE: Uniform spacing normalizes fast/slow drawing
#   3. CLASSIFY: Vertex-count-first tree + Hu moment refinement
# ═════════════════════════════════════════════════════════════

AUTO_CORRECT_THRESHOLD = 0.75
CANVAS = 500


def _smooth_points(pts, window=5):
    """Moving-average smooth to kill hand jitter."""
    if len(pts) < window:
        return pts
    kernel = np.ones(window) / window
    sx = np.convolve(pts[:, 0], kernel, mode='valid')
    sy = np.convolve(pts[:, 1], kernel, mode='valid')
    return np.column_stack([sx, sy])


def _resample(pts, n=64):
    """Resample trajectory to n equally-spaced points."""
    # Compute cumulative arc length
    diffs = np.diff(pts, axis=0)
    seg_lens = np.sqrt((diffs**2).sum(axis=1))
    cum_len = np.concatenate([[0], np.cumsum(seg_lens)])
    total = cum_len[-1]

    if total < 1e-6:
        return pts

    # Interpolate at uniform intervals
    targets = np.linspace(0, total, n)
    new_pts = np.zeros((n, 2))
    for i, t in enumerate(targets):
        idx = np.searchsorted(cum_len, t, side='right') - 1
        idx = np.clip(idx, 0, len(pts) - 2)
        seg = cum_len[idx+1] - cum_len[idx]
        if seg < 1e-8:
            frac = 0.0
        else:
            frac = (t - cum_len[idx]) / seg
        new_pts[i] = pts[idx] + frac * (pts[idx+1] - pts[idx])
    return new_pts


def _make_template(shape_name, n=64):
    """Generate an ideal contour for Hu moment matching."""
    t = np.linspace(0, 2*np.pi, n, endpoint=False)

    if shape_name == "CIRCLE":
        pts = np.column_stack([np.cos(t), np.sin(t)])
    elif shape_name == "OVAL":
        pts = np.column_stack([np.cos(t) * 1.5, np.sin(t)])
    elif shape_name == "TRIANGLE":
        angles = [0, 2*np.pi/3, 4*np.pi/3, 0]
        pts = np.array([[np.cos(a), np.sin(a)] for a in angles])
    elif shape_name == "SQUARE":
        pts = np.array([[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]], dtype=float)
    elif shape_name == "RECTANGLE":
        pts = np.array([[-1.5,-1],[1.5,-1],[1.5,1],[-1.5,1],[-1.5,-1]], dtype=float)
    elif shape_name == "DIAMOND":
        pts = np.array([[0,-1],[1,0],[0,1],[-1,0],[0,-1]], dtype=float)
    elif shape_name == "PENTAGON":
        a = np.linspace(0, 2*np.pi, 6)
        pts = np.column_stack([np.cos(a), np.sin(a)])
    elif shape_name == "HEXAGON":
        a = np.linspace(0, 2*np.pi, 7)
        pts = np.column_stack([np.cos(a), np.sin(a)])
    elif shape_name == "STAR":
        pts_list = []
        for i in range(5):
            outer = i * 2*np.pi/5 - np.pi/2
            inner = outer + np.pi/5
            pts_list.append([np.cos(outer), np.sin(outer)])
            pts_list.append([np.cos(inner)*0.4, np.sin(inner)*0.4])
        pts_list.append(pts_list[0])
        pts = np.array(pts_list)
    else:
        return None

    # Scale to canvas
    pts = pts - pts.min(axis=0)
    s = pts.max()
    if s > 0:
        pts = pts / s * (CANVAS * 0.8) + CANVAS * 0.1

    return pts.astype(np.int32).reshape(-1, 1, 2)


# Pre-build templates
_TEMPLATES = {}
for _sn in ["CIRCLE", "OVAL", "TRIANGLE", "SQUARE", "RECTANGLE",
            "DIAMOND", "PENTAGON", "HEXAGON", "STAR"]:
    _t = _make_template(_sn)
    if _t is not None:
        _TEMPLATES[_sn] = _t


def _hu_match(contour, top_candidates):
    """Compare contour against ideal templates using Hu moments.
    Returns the best matching shape from top_candidates.
    """
    best_shape = top_candidates[0]
    best_dist = float('inf')

    for name in top_candidates:
        tmpl = _TEMPLATES.get(name)
        if tmpl is None:
            continue
        try:
            dist = cv2.matchShapes(contour, tmpl, cv2.CONTOURS_MATCH_I2, 0)
            if dist < best_dist:
                best_dist = dist
                best_shape = name
        except:
            pass

    return best_shape, best_dist


def classify_shape(points):
    """Shape classifier v8 — vertex-count-first decision tree.
    Returns (shape, center, size, confidence, auto_corrected) or None.
    """
    if len(points) < MIN_DRAW_POINTS:
        return None

    pts = np.array(points, dtype=np.float64)

    # ── Stage 1: Smooth ──────────────────────────────────
    pts = _smooth_points(pts, window=5)
    if len(pts) < 5:
        return None

    # ── Stage 2: Resample to uniform spacing ─────────────
    pts = _resample(pts, n=64)

    # ── Basic geometry ───────────────────────────────────
    mn, mx = pts.min(axis=0), pts.max(axis=0)
    w, h = mx[0]-mn[0], mx[1]-mn[1]
    cx, cy = (mn[0]+mx[0])/2, (mn[1]+mx[1])/2
    diag = math.sqrt(w**2 + h**2)

    if diag < 0.02:
        return None

    # ── Build contour ────────────────────────────────────
    span = mx - mn
    span[span < 1e-6] = 1e-6
    pad = CANVAS * 0.1
    usable = CANVAS - 2 * pad
    scaled = ((pts - mn) / span * usable + pad).astype(np.int32)
    contour = scaled.reshape(-1, 1, 2)

    # ── Closedness (relaxed from 0.35 → 0.45) ───────────
    se = np.linalg.norm(pts[0] - pts[-1])
    closed = se < diag * 0.45
    if closed:
        contour = np.vstack([contour, contour[0:1]])

    # ── OpenCV metrics ───────────────────────────────────
    perimeter = cv2.arcLength(contour, closed)
    area = abs(cv2.contourArea(contour))
    circularity = (4 * math.pi * area) / (perimeter**2) if perimeter > 0 else 0

    # Aspect ratio
    if len(contour) >= 5:
        rect = cv2.minAreaRect(contour)
        rw, rh = rect[1]
        aspect = max(rw, rh) / max(min(rw, rh), 0.001)
    else:
        aspect = max(w, h) / max(min(w, h), 0.001)

    # Vertex count at 5% epsilon (loose for noisy data)
    approx = cv2.approxPolyDP(contour, 0.05 * perimeter, closed)
    verts = len(approx)

    # Linearity
    linearity = 1.0 - (min(w, h) / max(max(w, h), 0.001))

    # Solidity (for star detection)
    hull = cv2.convexHull(contour)
    hull_area = abs(cv2.contourArea(hull))
    solidity = area / hull_area if hull_area > 0 else 1.0

    print(f"[Aura-3D] v8b: closed={closed} circ={circularity:.2f} "
          f"verts={verts} asp={aspect:.1f} lin={linearity:.2f} sol={solidity:.2f}")

    # ═══════════════════════════════════════════════════════
    #  DECISION TREE v8b — balanced circularity + vertex
    #  Both signals are co-equal; neither dominates alone.
    #
    #  Layer 1: Open shapes (LINE/CURVE/ARC/ARROW)
    #  Layer 2: High circ (>0.75) → CIRCLE/OVAL always
    #  Layer 3: Low circ (<0.55) → trust vertex count
    #  Layer 4: Mid circ (0.55–0.75) → Hu moments decide
    #  Layer 5: Star via solidity
    # ═══════════════════════════════════════════════════════

    shape = None
    confidence = 0.0
    candidates = []

    if not closed:
        # ── OPEN SHAPES (LINE / ARC / CURVE / ARROW) ─────
        if linearity > 0.85:
            shape = "LINE"
            confidence = 0.5 + linearity * 0.4
        elif linearity > 0.5:
            if verts >= 4:
                shape = "ARROW"
                confidence = 0.55
            else:
                shape = "ARC"
                confidence = 0.50 + linearity * 0.3
        else:
            shape = "CURVE"
            confidence = 0.55

    # ══════════════════════════════════════════════════════
    #  CLOSED: Layer 2 — genuinely round (circ > 0.75)
    #  High circularity ALWAYS wins, regardless of noisy
    #  vertex count from approxPolyDP on hand-drawn data.
    # ══════════════════════════════════════════════════════

    elif circularity > 0.75:
        if aspect > 1.45:
            shape = "OVAL"
            confidence = 0.85
        else:
            shape = "CIRCLE"
            confidence = 0.85

    # ══════════════════════════════════════════════════════
    #  CLOSED: Layer 5 — deep concavities → STAR
    # ══════════════════════════════════════════════════════

    elif solidity < 0.55:
        shape = "STAR"
        confidence = 0.65
        candidates = ["STAR", "CIRCLE"]

    # ══════════════════════════════════════════════════════
    #  CLOSED: Layer 3 — clearly angular (circ < 0.55)
    #  Trust vertex count when circularity confirms it's
    #  NOT round.
    # ══════════════════════════════════════════════════════

    elif circularity < 0.55:
        if verts == 3:
            shape = "TRIANGLE"
            confidence = 0.80
            candidates = ["TRIANGLE", "DIAMOND"]
        elif verts == 4:
            if aspect < 1.3:
                shape = "SQUARE"
                confidence = 0.80
                candidates = ["SQUARE", "DIAMOND"]
            else:
                shape = "RECTANGLE"
                confidence = 0.75
                candidates = ["RECTANGLE", "SQUARE"]
        elif verts == 5:
            shape = "PENTAGON"
            confidence = 0.70
            candidates = ["PENTAGON", "HEXAGON"]
        elif verts == 6:
            shape = "HEXAGON"
            confidence = 0.65
            candidates = ["HEXAGON", "PENTAGON"]
        else:
            # Many verts + low circ = rough polygon attempt
            if aspect > 1.4:
                shape = "RECTANGLE"
                confidence = 0.50
                candidates = ["RECTANGLE", "OVAL"]
            else:
                shape = "HEXAGON"
                confidence = 0.45
                candidates = ["HEXAGON", "PENTAGON", "SQUARE"]

    # ══════════════════════════════════════════════════════
    #  CLOSED: Layer 4 — ambiguous zone (0.55 ≤ circ ≤ 0.75)
    #  Both circularity and verts are inconclusive.
    #  Let Hu moment template matching be the primary decider.
    # ══════════════════════════════════════════════════════

    else:
        if verts == 3 and circularity < 0.65:
            shape = "TRIANGLE"
            confidence = 0.65
            candidates = ["TRIANGLE", "CIRCLE", "DIAMOND"]
        elif verts == 4 and circularity < 0.65:
            if aspect < 1.3:
                shape = "SQUARE"
                confidence = 0.60
                candidates = ["SQUARE", "CIRCLE", "DIAMOND"]
            else:
                shape = "RECTANGLE"
                confidence = 0.60
                candidates = ["RECTANGLE", "OVAL", "SQUARE"]
        elif verts == 5:
            shape = "PENTAGON"
            confidence = 0.55
            candidates = ["PENTAGON", "CIRCLE", "HEXAGON"]
        elif verts == 6:
            shape = "HEXAGON"
            confidence = 0.55
            candidates = ["HEXAGON", "CIRCLE", "PENTAGON"]
        else:
            # Many verts in mid-circularity → probably round
            if aspect > 1.45:
                shape = "OVAL"
                confidence = 0.65
                candidates = ["OVAL", "RECTANGLE"]
            else:
                shape = "CIRCLE"
                confidence = 0.65
                candidates = ["CIRCLE", "HEXAGON", "SQUARE"]

    if shape is None:
        print("[Aura-3D] Could not classify")
        return None

    # ── Hu moment refinement ─────────────────────────────
    # If we have multiple candidates, use template matching as tiebreaker
    if len(candidates) >= 2:
        hu_shape, hu_dist = _hu_match(contour, candidates)
        if hu_shape != shape:
            print(f"[Aura-3D] Hu moments: {shape} -> {hu_shape} (dist={hu_dist:.3f})")
            shape = hu_shape
            confidence = max(confidence - 0.05, 0.40)

    print(f"[Aura-3D] => {shape} ({confidence:.0%})")

    auto_corrected = confidence >= AUTO_CORRECT_THRESHOLD
    return (shape, [cx, cy], diag/2.0, confidence, auto_corrected)


# ── MediaPipe callback ──────────────────────────────────────
_latest_result: HandLandmarkerResult | None = None

def _on_result(result: HandLandmarkerResult, image: Image, timestamp_ms: int):
    global _latest_result
    _latest_result = result


def main():
    global _latest_result

    if not os.path.exists(MODEL_PATH):
        print(f"Error: Hand landmarker model not found at:\n   {MODEL_PATH}")
        time.sleep(5)
        return

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

    cap = None
    for index in range(3):
        print(f"[Aura] Checking camera index {index}...")
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            print(f"[Aura] Camera found at index {index}")
            break
        if cap:
            cap.release()
        cap = None

    if cap is None:
        print("Error: Could not open any webcam.")
        time.sleep(5)
        return

    print("Aura-3D NPU Bridge Active!")
    print(f"Targeting Blender at {HOST}:{PORT}")
    print("PINCH to draw | POINT to erase | ESC to exit")

    frame_ts = 0
    is_drawing      = False
    draw_points     = []
    draw_start_time = 0
    status_text     = ""
    status_timer    = 0
    erase_cooldown  = 0
    fail_count      = 0
    MAX_FAILS       = 30

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                fail_count += 1
                if fail_count > MAX_FAILS:
                    print("[Aura-3D] Camera lost.")
                    break
                time.sleep(0.033)
                continue
            fail_count = 0

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)
            frame_ts += 33
            landmarker.detect_async(mp_image, frame_ts)

            result = _latest_result
            h, w, _ = frame.shape

            if result and result.hand_landmarks:
                for hand_landmarks in result.hand_landmarks:
                    center    = hand_landmarks[9]
                    thumb_tip = hand_landmarks[4]
                    index_tip = hand_landmarks[8]
                    dist_pinch = get_distance(thumb_tip, index_tip)

                    # ── AIR-DRAWING ───────────────────────────
                    if not is_drawing and dist_pinch < PINCH_START_THRESH:
                        is_drawing = True
                        draw_points = []
                        draw_start_time = time.time()
                        print("[Aura-3D] Drawing started")

                    if is_drawing:
                        if dist_pinch < PINCH_END_THRESH:
                            draw_points.append((index_tip.x, index_tip.y))
                        else:
                            is_drawing = False
                            dur = time.time() - draw_start_time
                            print(f"[Aura-3D] Drawing stopped ({len(draw_points)} pts, {dur:.1f}s)")

                            if dur < MIN_DRAW_TIME:
                                status_text  = "Too quick - draw slower"
                                status_timer = 45
                            else:
                                result_shape = classify_shape(draw_points)
                                if result_shape:
                                    sn, sc, ss, conf, ac = result_shape
                                    tag = " [AUTO-CORRECTED]" if ac else ""
                                    send_draw_2d(sn, sc, ss)
                                    status_text  = f"{sn} {conf:.0%}{tag}"
                                    status_timer = 90
                                else:
                                    status_text  = "Not recognized"
                                    status_timer = 30

                            draw_points = []

                    # Draw trail (ONLY while drawing)
                    if is_drawing and len(draw_points) > 1:
                        for i in range(1, len(draw_points)):
                            x1 = int(draw_points[i-1][0] * w)
                            y1 = int(draw_points[i-1][1] * h)
                            x2 = int(draw_points[i][0] * w)
                            y2 = int(draw_points[i][1] * h)
                            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 3)

                    # ── GESTURES ──────────────────────────────
                    if not is_drawing:
                        dist_fist = get_distance(index_tip, hand_landmarks[0])

                        # POINT detection: only index extended
                        middle_tip = hand_landmarks[12]
                        ring_tip   = hand_landmarks[16]
                        pinky_tip  = hand_landmarks[20]
                        is_pointing = (
                            index_tip.y < hand_landmarks[5].y and
                            middle_tip.y > hand_landmarks[9].y and
                            ring_tip.y > hand_landmarks[13].y and
                            pinky_tip.y > hand_landmarks[17].y and
                            dist_pinch > 0.06
                        )

                        gesture = GESTURE_MOVE
                        if is_pointing and erase_cooldown <= 0:
                            send_erase()
                            erase_cooldown = 30
                            status_text  = "ERASED!"
                            status_timer = 60
                            gesture = "POINT"
                        elif dist_pinch < 0.05:
                            gesture = GESTURE_PINCH
                        elif dist_fist < 0.2:
                            gesture = GESTURE_FIST
                        elif index_tip.y < hand_landmarks[5].y:
                            gesture = GESTURE_PALM

                        if erase_cooldown > 0:
                            erase_cooldown -= 1

                        if gesture != "POINT":
                            xyz = [center.x, 1.0 - center.y, center.z]
                            send_gesture(gesture, xyz)

                    # Draw landmarks
                    for lm in hand_landmarks:
                        cv2.circle(frame, (int(lm.x*w), int(lm.y*h)), 3, (0,255,0), -1)
                    for s_i, e_i in [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                        (0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),
                        (0,17),(17,18),(18,19),(19,20),(5,9),(9,13),(13,17)]:
                        p1, p2 = hand_landmarks[s_i], hand_landmarks[e_i]
                        cv2.line(frame, (int(p1.x*w),int(p1.y*h)), (int(p2.x*w),int(p2.y*h)), (0,200,0), 2)

                    # HUD
                    if is_drawing:
                        cv2.putText(frame, "DRAWING...", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,255), 2)
                        cv2.putText(frame, f"Points: {len(draw_points)}", (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1)
                    else:
                        cv2.putText(frame, f"Gesture: {gesture}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            # Status flash
            if status_timer > 0:
                color = (0,255,0) if "Not" not in status_text and "quick" not in status_text else (0,0,255)
                cv2.putText(frame, status_text, (10, h-30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                status_timer -= 1

            cv2.imshow("Aura-3D NPU Monitor", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except Exception as e:
        print(f"NPU Error: {str(e)}")
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
