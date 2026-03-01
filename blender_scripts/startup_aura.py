# ============================================================
#  Aura-3D  ·  Startup Automation
#  ──────────────────────────────────────────────────────────
#  This script is used to launch the entire project at once.
#  It runs the scene setup and registers the gesture bridge.
#
#  Uses importlib to properly load scripts as modules,
#  ensuring correct namespacing and __file__ resolution.
# ============================================================

import bpy
import os
import sys
import importlib.util


def _resolve_project_dirs():
    """Find the blender_scripts/ and project root dirs robustly."""
    # Method 1: __file__ is set (via --python or injected by launcher)
    try:
        me = os.path.realpath(__file__)
        scripts_dir = os.path.dirname(me)
        root_dir = os.path.dirname(scripts_dir)
        if os.path.exists(os.path.join(scripts_dir, "gesture_bridge.py")):
            return scripts_dir, root_dir
    except NameError:
        pass

    # Method 2: Check sys.path entries
    for p in sys.path:
        if os.path.isdir(p):
            # p might be scripts_dir
            if os.path.exists(os.path.join(p, "gesture_bridge.py")):
                return p, os.path.dirname(p)
            # p might be root_dir
            candidate = os.path.join(p, "blender_scripts")
            if os.path.exists(os.path.join(candidate, "gesture_bridge.py")):
                return candidate, p

    raise FileNotFoundError(
        "[Aura-3D] FATAL: Cannot locate blender_scripts directory. "
        "Ensure the project root is in sys.path."
    )


def _load_module_from_file(name, filepath):
    """Load a Python file as a proper module using importlib."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod   # register so sub-imports work
    spec.loader.exec_module(mod)
    return mod


def run_aura():
    print("\n" + "═" * 60)
    print("  🚀 Aura-3D  ·  Automated Startup")
    print("═" * 60)

    try:
        scripts_dir, root_dir = _resolve_project_dirs()
        print(f"[Aura-3D] Scripts dir: {scripts_dir}")
        print(f"[Aura-3D] Root dir:    {root_dir}")

        # Ensure both dirs are in sys.path for config imports
        for d in [scripts_dir, root_dir]:
            if d not in sys.path:
                sys.path.insert(0, d)

        # 1. Run Scene Setup
        setup_path = os.path.join(scripts_dir, "scene_setup.py")
        print(f"[Aura-3D] Initializing scene from: {setup_path}")
        if not os.path.exists(setup_path):
            raise FileNotFoundError(f"Missing script: {setup_path}")
        _load_module_from_file("aura_scene_setup", setup_path)

        # 2. Run Gesture Bridge (registers operators + UI panel)
        bridge_path = os.path.join(scripts_dir, "gesture_bridge.py")
        print(f"[Aura-3D] Registering Gesture Bridge from: {bridge_path}")
        if not os.path.exists(bridge_path):
            raise FileNotFoundError(f"Missing script: {bridge_path}")
        _load_module_from_file("aura_gesture_bridge", bridge_path)

        print("[Aura-3D] Setup complete.")
        print("  Bridge will auto-start in 3 seconds...")

        # Auto-start the bridge after a short delay
        def _auto_start_bridge():
            try:
                bpy.ops.aura.start_bridge()
                print("[Aura-3D] Bridge auto-started!")
            except Exception as ex:
                print(f"[Aura-3D] Auto-start failed: {ex}")
                print("  -> Press N in 3D Viewport -> 'Aura-3D' tab -> Start Bridge manually.")
            return None  # Don't repeat
        bpy.app.timers.register(_auto_start_bridge, first_interval=3.0)

    except Exception as e:
        import traceback
        print("\n" + "!" * 60)
        print("  CRITICAL ERROR DURING STARTUP")
        print(f"  {str(e)}")
        traceback.print_exc()
        print("!" * 60 + "\n")

    print("=" * 60 + "\n")


# Always register the delayed startup — works with both
# --python and --python-expr launch methods.
import bpy.app.timers
bpy.app.timers.register(run_aura, first_interval=1.0)
