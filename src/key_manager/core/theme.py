"""Visual theme: platform colors and color utility functions."""

# Platform accent colors (built-in platforms)
PLATFORM_COLORS = {
    "deepseek": (0.31, 0.27, 0.90, 1),
    "openai":   (0.06, 0.64, 0.50, 1),
    "bailian":  (0.98, 0.45, 0.09, 1),
    "mimo":     (0.55, 0.36, 0.76, 1),
    "zhipu":    (0.23, 0.45, 0.95, 1),
    "moonshot": (0.85, 0.55, 0.20, 1),
    "minimax":  (0.25, 0.35, 0.90, 1),
}

DEFAULT_CUSTOM_COLOR = (0.4, 0.4, 0.4, 1)


def accent_bg(color):
    """Light tinted background from an accent color (9% opacity)."""
    r, g, b, _ = color
    return (r, g, b, 0.09)


def accent_icon_bg(color):
    """Slightly stronger tinted background for icons (12% opacity)."""
    r, g, b, _ = color
    return (r, g, b, 0.12)
