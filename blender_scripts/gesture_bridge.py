# ============================================================
#  Aura-3D  ·  Gesture Bridge  (Main Entry Point)
#  ──────────────────────────────────────────────────────────
#  The COMPLETE integration script.  This is the one you use
#  in production.  It combines:
#
#    ✦ Non-blocking UDP listener  (via bpy.app.timers)
#    ✦ Screen → World coordinate mapping
#    ✦ Linear Interpolation (Lerp) for smooth motion
#    ✦ Gesture → Action dispatch  (Move / Scale / Color / Orbit)
#    ✦ Full Blender N-panel UI with live status
#
#  ▶ HOW TO RUN
#    1. Run  scene_setup.py  first (adds Suzanne + material)
#    2. Blender → Scripting → Open this file → Run Script
#    3. Press N → "Aura-3D" tab → click "Start Bridge"
#    4. In a separate terminal:
#         python external/test_sender.py
#    5. Watch Suzanne move, scale, change color, and the
#       camera orbit — all with cinematic smoothness.
#    6. Click "Stop Bridge" when done.
# ============================================================

import bpy
import socket
import json
import math
import sys
import os
from mathutils import Vector

# ── Import shared config ─────────────────────────────────────
_this_dir = os.path.dirname(os.path.realpath(__file__))
_root_dir = os.path.dirname(_this_dir)

# Add both to path for Blender's embedded Python
for d in [_this_dir, _root_dir]:
    if d not in sys.path:
        sys.path.append(d)

from config import (
    HOST, PORT, BUFFER_SIZE, TIMER_INTERVAL,
    LERP_FACTOR, SCREEN_MIN, SCREEN_MAX, WORLD_MIN, WORLD_MAX,
    GESTURE_MOVE, GESTURE_OPEN, GESTURE_PINCH, GESTURE_FIST, GESTURE_PALM,
)

# ── Local overrides (you can tweak these here) ───────────────
CONFIDENCE_THRESHOLD = 0.5   # ignore noisy frames below this


# ═════════════════════════════════════════════════════════════
#  MATH  ·  Lerp & Coordinate Mapping
# ═════════════════════════════════════════════════════════════

def lerp(current: float, target: float, factor: float) -> float:
    """Linear interpolation between two floats.

    factor = 0.0  → no movement  (stays at current)
    factor = 1.0  → instant snap (jumps to target)
    factor ≈ 0.15 → smooth cinematic blend
    """
    return current + (target - current) * factor


def lerp_vec(current: Vector, target: Vector, factor: float) -> Vector:
    """Lerp each axis of a 3D vector independently."""
    return Vector((
        lerp(current.x, target.x, factor),
        lerp(current.y, target.y, factor),
        lerp(current.z, target.z, factor),
    ))


def screen_to_world(value: float) -> float:
    """Remap a normalised screen coordinate [0..1] to world space [-5..+5]."""
    t = (value - SCREEN_MIN) / (SCREEN_MAX - SCREEN_MIN)
    return WORLD_MIN + t * (WORLD_MAX - WORLD_MIN)


def screen_to_world_vec(xyz: list) -> Vector:
    """Convert a 3-element normalised list → world-space Vector."""
    return Vector((
        screen_to_world(xyz[0]),
        screen_to_world(xyz[1]),
        screen_to_world(xyz[2]),
    ))


# ═════════════════════════════════════════════════════════════
#  GESTURE HANDLERS
# ═════════════════════════════════════════════════════════════

# ── Color palette for FIST cycling ───────────────────────────
_COLORS = [
    (1.0, 0.2, 0.3, 1.0),   # Red
    (0.2, 0.8, 0.4, 1.0),   # Green
    (0.1, 0.5, 1.0, 1.0),   # Blue
    (1.0, 0.8, 0.0, 1.0),   # Gold
    (0.7, 0.2, 0.9, 1.0),   # Purple
    (0.0, 0.8, 0.7, 1.0),   # Teal (brand)
]
_color_idx = 0


def handle_move(obj, world_target):
    """Smoothly translate the object toward the mapped position."""
    obj.location = lerp_vec(Vector(obj.location), world_target, LERP_FACTOR)


def handle_pinch(obj, world_target):
    """Scale the object based on the X-axis value.
    Screen x=0 → scale 0.5,  x=1 → scale 2.5."""
    t = (world_target.x - WORLD_MIN) / (WORLD_MAX - WORLD_MIN)
    raw = 0.5 + t * 2.0
    target_scale = Vector((raw, raw, raw))
    obj.scale = lerp_vec(Vector(obj.scale), target_scale, LERP_FACTOR)


def handle_fist(obj, world_target):
    """Cycle through the color palette on the object's material."""
    global _color_idx

    # Ensure the object has a material
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="Aura_DynMat")
        mat.use_nodes = True
        obj.data.materials.append(mat)

    mat = obj.data.materials[0]
    if mat and mat.use_nodes:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            color = _COLORS[_color_idx % len(_COLORS)]
            bsdf.inputs["Base Color"].default_value = color
            _color_idx += 1
            print(f"[Aura-3D]  🎨 Color → RGBA{color}")


def handle_palm(obj, world_target):
    """Orbit the camera around the origin, driven by the hand's X position."""
    camera = bpy.data.objects.get("Camera")
    if not camera:
        print("[Aura-3D] ⚠ No Camera in scene — PALM skipped.")
        return

    # Map world X to a full 360° sweep
    t = (world_target.x - WORLD_MIN) / (WORLD_MAX - WORLD_MIN)
    angle = t * math.tau  # 0 → 2π
    radius = 8.0

    orbit_target = Vector((
        radius * math.cos(angle),
        radius * math.sin(angle),
        camera.location.z,
    ))
    camera.location = lerp_vec(Vector(camera.location), orbit_target, LERP_FACTOR)

    # Point camera at origin
    look_dir = Vector((0, 0, 0)) - Vector(camera.location)
    camera.rotation_euler = look_dir.to_track_quat('-Z', 'Y').to_euler()


# ── Dispatch table ───────────────────────────────────────────
_DISPATCH = {
    GESTURE_MOVE:  handle_move,
    GESTURE_OPEN:  handle_move,
    GESTURE_PINCH: handle_pinch,
    GESTURE_FIST:  handle_fist,
    GESTURE_PALM:  handle_palm,
}


# ═════════════════════════════════════════════════════════════
#  UDP SERVER  (non-blocking via bpy.app.timers)
# ═════════════════════════════════════════════════════════════

_udp_socket = None
_is_running = False
_packet_count = 0


def _open_socket():
    """Create a non-blocking UDP socket and bind it."""
    global _udp_socket
    try:
        _udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _udp_socket.setblocking(False)
        _udp_socket.bind((HOST, PORT))
        print(f"[Aura-3D] ✔ Bridge bound to {HOST}:{PORT}")
    except Exception as e:
        print(f"[Aura-3D] ❌ Failed to open socket: {e}")
        raise e


def _close():
    global _udp_socket
    if _udp_socket:
        _udp_socket.close()
        _udp_socket = None
        print("[Aura-3D] ✔ Socket closed.")


def _tick():
    """Timer callback — poll for one UDP packet, dispatch to handler."""
    global _is_running, _packet_count

    if not _is_running or _udp_socket is None:
        return None

    try:
        data, _ = _udp_socket.recvfrom(BUFFER_SIZE)
        payload = json.loads(data.decode("utf-8"))

        gesture    = payload.get("gesture", "UNKNOWN")
        xyz        = payload.get("xyz", [0.5, 0.5, 0.5])
        confidence = payload.get("confidence", 0.0)

        if confidence < CONFIDENCE_THRESHOLD:
            return TIMER_INTERVAL

        _packet_count += 1
        world_xyz = screen_to_world_vec(xyz)
        handler   = _DISPATCH.get(gesture)
        obj       = bpy.context.active_object

        if handler and obj:
            handler(obj, world_xyz)
        elif not obj:
            if _packet_count % 120 == 1:
                print("[Aura-3D] ⚠ No active object selected!")
        else:
            print(f"[Aura-3D] ⚠ Unknown gesture: {gesture}")

    except BlockingIOError:
        pass
    except json.JSONDecodeError as e:
        print(f"[Aura-3D] ⚠ Bad JSON: {e}")
    except Exception as e:
        print(f"[Aura-3D] ⚠ Error: {e}")

    return TIMER_INTERVAL


# ═════════════════════════════════════════════════════════════
#  BLENDER OPERATORS
# ═════════════════════════════════════════════════════════════

class AURA_OT_StartBridge(bpy.types.Operator):
    """Launch the full Aura-3D gesture bridge."""
    bl_idname      = "aura.start_bridge"
    bl_label       = "Start Bridge"
    bl_description = "Open UDP socket + begin gesture → 3D action loop"

    def execute(self, context):
        global _is_running, _packet_count
        if _is_running:
            self.report({"WARNING"}, "Bridge is already running.")
            return {"CANCELLED"}

        _open_socket()
        _is_running = True
        _packet_count = 0
        bpy.app.timers.register(_tick, first_interval=TIMER_INTERVAL)
        self.report({"INFO"}, f"Aura-3D Bridge live on {HOST}:{PORT}")
        print(f"\n[Aura-3D] ═══  BRIDGE STARTED  {HOST}:{PORT}  ═══")
        return {"FINISHED"}


class AURA_OT_StopBridge(bpy.types.Operator):
    """Shut down the Aura-3D gesture bridge."""
    bl_idname      = "aura.stop_bridge"
    bl_label       = "Stop Bridge"
    bl_description = "Close UDP socket + stop listening"

    def execute(self, context):
        global _is_running
        _is_running = False
        _close()
        self.report({"INFO"}, f"Bridge stopped. ({_packet_count} packets)")
        print(f"[Aura-3D] ═══  BRIDGE STOPPED  ({_packet_count} packets)  ═══\n")
        return {"FINISHED"}


# ═════════════════════════════════════════════════════════════
#  UI PANEL  (N-panel in 3D Viewport → "Aura-3D" tab)
# ═════════════════════════════════════════════════════════════

class AURA_PT_MainPanel(bpy.types.Panel):
    bl_label       = "Aura-3D"
    bl_idname      = "AURA_PT_main_panel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Aura-3D"

    def draw(self, context):
        layout = self.layout

        # ── Header ───────────────────────────────────────────
        box = layout.box()
        box.label(text="Gesture Bridge", icon="OUTLINER_OB_ARMATURE")
        box.label(text=f"UDP endpoint:  {HOST}:{PORT}")

        # ── Start / Stop ─────────────────────────────────────
        row = layout.row(align=True)
        row.scale_y = 1.4
        row.operator("aura.start_bridge", icon="PLAY")
        row.operator("aura.stop_bridge",  icon="SNAP_FACE")

        # ── Status ───────────────────────────────────────────
        if _is_running:
            layout.label(text=f"● LIVE  ({_packet_count} packets)", icon="REC")
        else:
            layout.label(text="○ Idle", icon="RADIOBUT_OFF")

        # ── Reference ────────────────────────────────────────
        layout.separator()
        col = layout.column(align=True)
        col.scale_y = 0.85
        col.label(text="Gesture Map:", icon="INFO")
        col.label(text="  MOVE / OPEN  →  Translate object")
        col.label(text="  PINCH        →  Scale object")
        col.label(text="  FIST         →  Cycle color")
        col.label(text="  PALM         →  Orbit camera")

        layout.separator()
        col = layout.column(align=True)
        col.label(text=f"Lerp:  {LERP_FACTOR}   |   Gate:  {CONFIDENCE_THRESHOLD}")


# ═════════════════════════════════════════════════════════════
#  REGISTRATION
# ═════════════════════════════════════════════════════════════

_classes = (
    AURA_OT_StartBridge,
    AURA_OT_StopBridge,
    AURA_PT_MainPanel,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    global _is_running
    _is_running = False
    _close()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__" or True:
    register()
    print("[Aura-3D] ✔ Gesture Bridge registered.")
    print("          Press N in 3D Viewport → Aura-3D tab → Start Bridge")
