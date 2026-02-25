#!/usr/bin/env python3
# ============================================================
#  Aura-3D  ·  Test Sender
#  ──────────────────────────────────────────────────────────
#  A standalone Python script that simulates gesture data
#  from an NPU pipeline by sending UDP packets to the
#  Blender bridge.
#
#  ▶ This runs OUTSIDE Blender, in a normal terminal.
#
#  Usage:
#    python test_sender.py                 (default port 9090)
#    python test_sender.py --port 9090     (explicit port)
#    python test_sender.py --loop          (repeat forever)
#    python test_sender.py --fps 60        (send at 60 Hz)
#
#  The script sends a realistic sequence of gestures:
#    1. MOVE  — sine-wave trajectory   (60 frames)
#    2. PINCH — gradual scale increase (20 frames)
#    3. FIST  — color change trigger   (1 frame)
#    4. PALM  — camera orbit sweep     (40 frames)
# ============================================================

import socket
import json
import time
import math
import argparse
import os
import sys

# ── Import shared config ───────────────────────────────────
_this_dir = os.path.dirname(os.path.realpath(__file__))
_root_dir = os.path.dirname(_this_dir)
if _root_dir not in sys.path:
    sys.path.append(_root_dir)

from config import (
    HOST as DEFAULT_HOST, 
    PORT as DEFAULT_PORT,
    GESTURE_MOVE, GESTURE_OPEN, GESTURE_PINCH, GESTURE_FIST, GESTURE_PALM
)

DEFAULT_FPS = 30


def build_sequence():
    """Generate a list of gesture payloads that exercise every handler."""
    seq = []

    # 1 · MOVE — object follows a smooth sine-wave path
    for i in range(60):
        seq.append({
            "gesture": GESTURE_MOVE,
            "xyz": [
                0.5 + 0.3 * math.sin(i * 0.2),
                0.5,
                0.5 + 0.2 * math.cos(i * 0.2),
            ],
            "confidence": 0.92,
        })

    # 2 · PINCH — gradually increase scale
    for i in range(20):
        seq.append({
            "gesture": GESTURE_PINCH,
            "xyz": [0.3 + i * 0.02, 0.5, 0.5],
            "confidence": 0.88,
        })

    # 3 · FIST — trigger a color change
    seq.append({
        "gesture": GESTURE_FIST,
        "xyz": [0.5, 0.5, 0.5],
        "confidence": 0.95,
    })

    # 4 · PALM — sweep the camera around the scene
    for i in range(40):
        seq.append({
            "gesture": GESTURE_PALM,
            "xyz": [0.5 + 0.4 * math.sin(i * 0.1), 0.5, 0.5],
            "confidence": 0.90,
        })

    return seq


def main():
    parser = argparse.ArgumentParser(
        description="Aura-3D Test Sender — simulates gesture UDP packets."
    )
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Target hostname  (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Target UDP port  (default: {DEFAULT_PORT})")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS,
                        help=f"Packets per second  (default: {DEFAULT_FPS})")
    parser.add_argument("--loop", action="store_true",
                        help="Loop the sequence forever (Ctrl+C to stop)")
    args = parser.parse_args()

    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / args.fps

    print(f"\n  Aura-3D Test Sender")
    print(f"  Target : {args.host}:{args.port}")
    print(f"  Rate   : {args.fps} Hz")
    print(f"  Mode   : {'loop (Ctrl+C to stop)' if args.loop else 'single pass'}")
    print(f"  {'─' * 40}\n")

    try:
        pass_num = 0
        while True:
            pass_num += 1
            sequence = build_sequence()
            total = len(sequence)

            if args.loop:
                print(f"  ── Pass #{pass_num} ({total} packets) ──")

            for i, payload in enumerate(sequence):
                payload["timestamp"] = time.time()
                raw = json.dumps(payload).encode("utf-8")
                sock.sendto(raw, (args.host, args.port))

                gesture = payload["gesture"]
                xyz = payload["xyz"]
                print(f"  TX [{i+1:>4}/{total}]  "
                      f"{gesture:<6}  "
                      f"xyz=[{xyz[0]:.2f}, {xyz[1]:.2f}, {xyz[2]:.2f}]")

                time.sleep(interval)

            if not args.loop:
                break

        print(f"\n  ✔ Sequence complete ({total} packets sent).\n")

    except KeyboardInterrupt:
        print(f"\n\n  ✖ Stopped by user (pass #{pass_num}).\n")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
