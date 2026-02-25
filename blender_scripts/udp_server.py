# ============================================================
#  Aura-3D  ·  UDP Server
#  ──────────────────────────────────────────────────────────
#  A non-blocking UDP listener that runs INSIDE Blender.
#  It uses bpy.app.timers to poll the socket at ~60 Hz so
#  the Blender UI never freezes.
#
#  A panel named "Aura-3D Bridge" appears in the 3D Viewport
#  sidebar (press N) with Start / Stop buttons.
#
#  This is the standalone network layer.  For the full
#  integration with gesture handlers and Lerp smoothing,
#  see  gesture_bridge.py  instead.
#
#  ▶ HOW TO RUN
#    1. Blender → Scripting tab → Open this file → Run Script
#    2. Press N in the 3D Viewport → "Aura-3D" tab
#    3. Click "Start Server"
#    4. In a separate terminal:
#         python external/test_sender.py
#    5. Watch the Blender system console for received data
# ============================================================

import bpy
import socket
import json
import sys
import os

# ── Import shared config ───────────────────────────────────
_this_dir = os.path.dirname(os.path.realpath(__file__))
_root_dir = os.path.dirname(_this_dir)

# Add both to path for Blender's embedded Python
for d in [_this_dir, _root_dir]:
    if d not in sys.path:
        sys.path.append(d)

from config import HOST, PORT, BUFFER_SIZE, TIMER_INTERVAL


# ═════════════════════════════════════════════════════════════
#  INTERNAL STATE
# ═════════════════════════════════════════════════════════════

_udp_socket = None    # the bound UDP socket
_is_running = False   # whether the timer loop is active
_packet_count = 0     # packets received this session


# ═════════════════════════════════════════════════════════════
#  SOCKET HELPERS
# ═════════════════════════════════════════════════════════════

def _open_socket():
    """Create a non-blocking UDP socket and bind it."""
    global _udp_socket
    try:
        _udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _udp_socket.setblocking(False)
        _udp_socket.bind((HOST, PORT))
        print(f"[Aura-3D] ✔ Socket bound → {HOST}:{PORT}")
    except Exception as e:
        print(f"[Aura-3D] ❌ Port {PORT} is busy: {e}")
        raise e


def _close_socket():
    """Safely close the socket."""
    global _udp_socket
    if _udp_socket:
        _udp_socket.close()
        _udp_socket = None
        print("[Aura-3D] ✔ Socket closed.")


# ═════════════════════════════════════════════════════════════
#  TIMER CALLBACK  (the non-blocking heartbeat)
# ═════════════════════════════════════════════════════════════

def _poll_socket():
    """Called by bpy.app.timers at ~60 Hz.
    Reads one UDP packet per tick (non-blocking)."""
    global _is_running, _packet_count

    if not _is_running or _udp_socket is None:
        return None  # returning None removes the timer

    try:
        data, addr = _udp_socket.recvfrom(BUFFER_SIZE)
        payload = json.loads(data.decode("utf-8"))
        _packet_count += 1
        _on_message(payload)

    except BlockingIOError:
        pass  # no data available — totally normal
    except json.JSONDecodeError as e:
        print(f"[Aura-3D] ⚠ Bad JSON: {e}")
    except Exception as e:
        print(f"[Aura-3D] ⚠ Socket error: {e}")

    return TIMER_INTERVAL  # reschedule for the next tick


def _on_message(payload: dict):
    """Handle one parsed JSON message.
    In this standalone server, we just log it and do a simple demo action."""
    gesture = payload.get("gesture", "UNKNOWN")
    xyz     = payload.get("xyz", [0.0, 0.0, 0.0])
    conf    = payload.get("confidence", 0.0)

    print(f"[Aura-3D] RX #{_packet_count:>4}  "
          f"gesture={gesture:<6}  xyz=[{xyz[0]:.2f}, {xyz[1]:.2f}, {xyz[2]:.2f}]  "
          f"conf={conf:.2f}")

    # Demo: move active object up slightly on MOVE gesture
    obj = bpy.context.active_object
    if obj and gesture == "MOVE":
        obj.location.z += 0.05


# ═════════════════════════════════════════════════════════════
#  BLENDER OPERATORS
# ═════════════════════════════════════════════════════════════

class AURA_OT_StartServer(bpy.types.Operator):
    """Start the Aura-3D UDP listener."""
    bl_idname  = "aura.start_server"
    bl_label   = "Start Server"
    bl_description = "Open the UDP socket and begin listening"

    def execute(self, context):
        global _is_running, _packet_count
        if _is_running:
            self.report({"WARNING"}, "Server is already running.")
            return {"CANCELLED"}

        _open_socket()
        _is_running = True
        _packet_count = 0
        bpy.app.timers.register(_poll_socket, first_interval=TIMER_INTERVAL)
        self.report({"INFO"}, f"Aura-3D server started on {HOST}:{PORT}")
        print(f"\n[Aura-3D] ═══  SERVER STARTED  {HOST}:{PORT}  ═══")
        return {"FINISHED"}


class AURA_OT_StopServer(bpy.types.Operator):
    """Stop the Aura-3D UDP listener."""
    bl_idname  = "aura.stop_server"
    bl_label   = "Stop Server"
    bl_description = "Close the UDP socket and stop listening"

    def execute(self, context):
        global _is_running
        _is_running = False
        _close_socket()
        self.report({"INFO"}, f"Server stopped. ({_packet_count} packets received)")
        print(f"[Aura-3D] ═══  SERVER STOPPED  ({_packet_count} packets)  ═══\n")
        return {"FINISHED"}


# ═════════════════════════════════════════════════════════════
#  UI PANEL  (N-panel in 3D Viewport)
# ═════════════════════════════════════════════════════════════

class AURA_PT_ServerPanel(bpy.types.Panel):
    """Aura-3D server controls in the 3D Viewport sidebar."""
    bl_label       = "Aura-3D Bridge"
    bl_idname      = "AURA_PT_server_panel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Aura-3D"

    def draw(self, context):
        layout = self.layout

        layout.label(text=f"UDP  {HOST}:{PORT}", icon="URL")

        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("aura.start_server", icon="PLAY")
        row.operator("aura.stop_server",  icon="SNAP_FACE")

        if _is_running:
            layout.label(text=f"● LIVE  ({_packet_count} pkts)", icon="REC")
        else:
            layout.label(text="○ Idle", icon="RADIOBUT_OFF")


# ═════════════════════════════════════════════════════════════
#  REGISTRATION
# ═════════════════════════════════════════════════════════════

_classes = (
    AURA_OT_StartServer,
    AURA_OT_StopServer,
    AURA_PT_ServerPanel,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    global _is_running
    _is_running = False
    _close_socket()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__" or True:
    register()
    print("[Aura-3D] ✔ UDP Server registered.")
    print("          Open N-panel (N) → Aura-3D tab → Start Server")
