# ============================================================================
# Aura-3D | Utility — Coordinate Mapper
# ============================================================================
# Purpose : Convert normalised screen-space coordinates [0.0 … 1.0]
#           to Blender world-space coordinates [-5.0 … +5.0].
# ============================================================================


def screen_to_world(x, y, z, world_min=-5.0, world_max=5.0):
    """
    Map normalised screen-space [0.0 … 1.0] to world-space [min … max].

    Args:
        x, y, z : float — normalised coordinates (0.0 to 1.0)
        world_min : float — lower bound of world-space range (default -5.0)
        world_max : float — upper bound of world-space range (default +5.0)

    Returns:
        tuple(float, float, float) — (world_x, world_y, world_z)
    """
    span = world_max - world_min
    wx = world_min + x * span
    wy = world_min + y * span
    wz = world_min + z * span
    return (wx, wy, wz)


def world_to_screen(wx, wy, wz, world_min=-5.0, world_max=5.0):
    """
    Inverse mapping: world-space → normalised screen-space.

    Args:
        wx, wy, wz : float — world-space coordinates
        world_min, world_max : float — world-space range bounds

    Returns:
        tuple(float, float, float) — (screen_x, screen_y, screen_z)
    """
    span = world_max - world_min
    if span == 0:
        return (0.0, 0.0, 0.0)
    sx = (wx - world_min) / span
    sy = (wy - world_min) / span
    sz = (wz - world_min) / span
    return (sx, sy, sz)


def clamp(value, min_val=0.0, max_val=1.0):
    """Clamp a value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def clamp_screen(x, y, z):
    """Clamp all coordinates to valid screen-space [0.0 … 1.0]."""
    return (clamp(x), clamp(y), clamp(z))
