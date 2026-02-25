# ============================================================
#  Aura-3D  ·  Scene Setup
#  ──────────────────────────────────────────────────────────
#  Initializes the Blender scene for gesture-controlled work.
#  Removes the default Cube, adds a Suzanne (Monkey Head),
#  positions and rotates it, and applies a branded material.
#
#  ▶ HOW TO RUN
#    Blender → Scripting tab → Open this file → Run Script
# ============================================================

import bpy
import math


def enable_developer_extras():
    """Turn on 'Developer Extras' in Preferences.
    This enables Python tooltips, operator search, etc."""
    bpy.context.preferences.view.show_developer_ui = True
    print("[Aura-3D] ✔ Developer Extras enabled.")


def clear_default_objects():
    """Remove the default Cube, Light, and Camera for a clean start."""
    defaults = ["Cube"]
    for name in defaults:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
            print(f"[Aura-3D] ✔ Removed '{name}'.")
        else:
            print(f"[Aura-3D] ⏭ '{name}' not found — skipping.")


def add_suzanne(location=(0, 5, 2), rotation_z_deg=45, size=1.5):
    """Add a Suzanne mesh, position it, and apply a material.

    Args:
        location:       (x, y, z) world-space position.
        rotation_z_deg: rotation around Z-axis in degrees.
        size:           scale factor for the mesh.

    Returns:
        The newly created Blender object.
    """
    bpy.ops.mesh.primitive_monkey_add(
        size=size,
        location=location,
        rotation=(0, 0, math.radians(rotation_z_deg)),
    )

    suzanne = bpy.context.active_object
    suzanne.name = "Aura_Suzanne"

    # ── Material ─────────────────────────────────────────────
    mat = bpy.data.materials.new(name="Aura_BrandMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.0, 0.8, 0.7, 1.0)  # Teal
        bsdf.inputs["Roughness"].default_value = 0.35
        bsdf.inputs["Metallic"].default_value = 0.1

    suzanne.data.materials.append(mat)
    bpy.ops.object.shade_smooth()

    print(f"[Aura-3D] ✔ Suzanne added → location={location}, "
          f"rot_Z={rotation_z_deg}°, material='{mat.name}'")
    return suzanne


def setup_viewport():
    """Switch the 3D viewport shading to Material Preview
    so the material is visible immediately."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    break


# ── Entry Point ──────────────────────────────────────────────
def main():
    print("\n" + "═" * 55)
    print("  Aura-3D  ·  Scene Setup")
    print("═" * 55)

    enable_developer_extras()
    clear_default_objects()
    suzanne = add_suzanne()
    setup_viewport()

    print("═" * 55)
    print("  ✔ Scene ready. Suzanne is your gesture target.")
    print("═" * 55 + "\n")


main()
