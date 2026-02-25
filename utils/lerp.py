# ============================================================================
# Aura-3D | Utility — Linear Interpolation (Lerp)
# ============================================================================
# Purpose : Provide smooth interpolation for all coordinate/value updates
#           to achieve "Cinematic Smoothness" as required by spec.
#
# Default t = 0.15 — fast enough to feel responsive, slow enough
# to eliminate jitter from raw hand-tracking data.
# ============================================================================


def lerp(a, b, t=0.15):
    """
    Scalar linear interpolation.

    Args:
        a : float — current value
        b : float — target value
        t : float — interpolation factor (0.0 = stay at a, 1.0 = jump to b)

    Returns:
        float — interpolated value
    """
    return a + (b - a) * t


def lerp_vec3(current, target, t=0.15):
    """
    3-component vector linear interpolation.

    Args:
        current : tuple/list of 3 floats — current (x, y, z)
        target  : tuple/list of 3 floats — target (x, y, z)
        t       : float — interpolation factor

    Returns:
        tuple(float, float, float) — smoothly interpolated position
    """
    return (
        lerp(current[0], target[0], t),
        lerp(current[1], target[1], t),
        lerp(current[2], target[2], t),
    )


def lerp_color(current, target, t=0.15):
    """
    4-component color interpolation (RGBA).

    Args:
        current : tuple/list of 4 floats — current RGBA
        target  : tuple/list of 4 floats — target RGBA
        t       : float — interpolation factor

    Returns:
        tuple(float, float, float, float) — smoothly interpolated color
    """
    return (
        lerp(current[0], target[0], t),
        lerp(current[1], target[1], t),
        lerp(current[2], target[2], t),
        lerp(current[3], target[3], t),
    )


class SmoothValue:
    """
    Stateful smoother that tracks a 3D position and lerps toward targets.

    Usage:
        smoother = SmoothValue(initial=(0, 0, 0), t=0.15)
        smooth_pos = smoother.update(new_target)
    """

    def __init__(self, initial=(0.0, 0.0, 0.0), t=0.15):
        self.current = tuple(initial)
        self.t = t

    def update(self, target):
        """Lerp toward target and return the new smoothed position."""
        self.current = lerp_vec3(self.current, target, self.t)
        return self.current

    def snap(self, position):
        """Immediately jump to a position (no interpolation)."""
        self.current = tuple(position)
        return self.current

    def distance_to(self, target):
        """Euclidean distance from current to target."""
        dx = self.current[0] - target[0]
        dy = self.current[1] - target[1]
        dz = self.current[2] - target[2]
        return (dx * dx + dy * dy + dz * dz) ** 0.5
