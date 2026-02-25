# ============================================================
#  Aura-3D  ·  Modal Listener
#  ──────────────────────────────────────────────────────────
#  A Blender Modal Operator that runs a non-blocking loop,
#  printing "Listening..." to the system console each tick
#  WITHOUT freezing the Blender UI.
#
#  This is a foundation script that proves non-blocking
#  execution inside Blender — the pattern used by the
#  full gesture bridge.
#
#  ▶ HOW TO RUN
#    1. Blender → Scripting tab → Open this file → Run Script
#    2. Press F3 → search "Aura: Start Listener" → click it
#    3. Open system console:  Window → Toggle System Console
#    4. Press ESC anytime to stop the listener
# ============================================================

import bpy


class AURA_OT_ModalListener(bpy.types.Operator):
    """Aura-3D: Non-blocking listener loop (ESC to stop)."""

    bl_idname = "aura.modal_listener"
    bl_label = "Aura: Start Listener"
    bl_description = (
        "Start the Aura-3D demo listener. "
        "Prints to the system console every 0.5 seconds. "
        "Press ESC to cancel."
    )

    _timer = None
    _tick = 0

    # ── Start ────────────────────────────────────────────────
    def invoke(self, context, event):
        # Create a timer event that fires every 0.5 seconds
        self._timer = context.window_manager.event_timer_add(
            time_step=0.5,
            window=context.window,
        )
        # Register this operator as a modal handler
        context.window_manager.modal_handler_add(self)

        AURA_OT_ModalListener._tick = 0
        self.report({"INFO"}, "[Aura-3D] Listener started — press ESC to stop.")
        print("\n[Aura-3D] ═══  Modal Listener STARTED  ═══")
        return {"RUNNING_MODAL"}

    # ── Each Event ───────────────────────────────────────────
    def modal(self, context, event):
        # Stop on ESC
        if event.type == "ESC":
            self._cleanup(context)
            return {"CANCELLED"}

        # On each timer tick, print the heartbeat
        if event.type == "TIMER":
            AURA_OT_ModalListener._tick += 1
            print(f"[Aura-3D] Listening...  (tick #{self._tick})")

        # PASS_THROUGH lets other Blender events work normally
        return {"PASS_THROUGH"}

    # ── Cleanup ──────────────────────────────────────────────
    def _cleanup(self, context):
        context.window_manager.event_timer_remove(self._timer)
        print(f"[Aura-3D] ═══  Modal Listener STOPPED  ═══  "
              f"(ran for {self._tick} ticks)\n")
        self.report({"INFO"}, "[Aura-3D] Listener stopped.")


# ── Register / Unregister ────────────────────────────────────
def register():
    bpy.utils.register_class(AURA_OT_ModalListener)


def unregister():
    bpy.utils.unregister_class(AURA_OT_ModalListener)


if __name__ == "__main__" or True:
    register()
    print("[Aura-3D] ✔ Modal Listener registered.")
    print("          Press F3 → search 'Aura: Start Listener'")
