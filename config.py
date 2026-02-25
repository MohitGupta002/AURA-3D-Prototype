# ============================================================
#  Aura-3D  |  Bridge Configuration
#  Shared constants for all Blender-side scripts.
# ============================================================

# ── Network ──────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 9090
BUFFER_SIZE = 1024  # bytes per UDP datagram

# ── Coordinate Mapping ───────────────────────────────────────
# Screen-space input from NPU pipeline is normalized [0.0, 1.0].
# We remap to Blender world-space bounds.
SCREEN_MIN = 0.0
SCREEN_MAX = 1.0
WORLD_MIN = -5.0
WORLD_MAX = 5.0

# ── Smoothing ────────────────────────────────────────────────
# Linear interpolation factor  (0 = no movement, 1 = instant snap)
LERP_FACTOR = 0.15

# ── Timer ────────────────────────────────────────────────────
# How often (seconds) the non-blocking listener polls for data.
# ~60 Hz ≈ 0.016 s
TIMER_INTERVAL = 0.016

# ── Gesture Tags ─────────────────────────────────────────────
# Canonical gesture names expected in the JSON protocol.
GESTURE_MOVE  = "MOVE"
GESTURE_OPEN  = "OPEN"
GESTURE_PINCH = "PINCH"
GESTURE_FIST  = "FIST"
GESTURE_PALM  = "PALM"

# Mapping: gesture name → handler function name (resolved at runtime)
GESTURE_ACTIONS = {
    GESTURE_MOVE:  "handle_move",
    GESTURE_OPEN:  "handle_move",     # OPEN hand also translates
    GESTURE_PINCH: "handle_pinch",
    GESTURE_FIST:  "handle_fist",
    GESTURE_PALM:  "handle_palm",
}
