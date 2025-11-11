# -------------------- color_utils.py (start)
import numpy as np


# -------------------- OKLCH → sRGB converter (start)
def oklch_to_srgb(oklch):
    """Convert OKLCH → linear sRGB (floats 0–1)."""
    L, C, H = oklch
    h_rad = np.deg2rad(H)
    a = np.cos(h_rad) * C
    b = np.sin(h_rad) * C

    # --- Oklab → LMS non-linear space ---
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    # --- Cube (linearize) ---
    l = l_**3
    m = m_**3
    s = s_**3

    # --- LMS → sRGB ---
    r = (+4.0767416621 * l) - (3.3077115913 * m) + (0.2309699292 * s)
    g = (-1.2684380046 * l) + (2.6097574011 * m) - (0.3413193965 * s)
    b = (-0.0045160939 * l) - (0.0052037247 * m) + (1.0107199036 * s)

    return np.clip([r, g, b], 0, 1)


# -------------------- OKLCH → sRGB converter (end)


# -------------------- OKLCH → HEX converter (start)
def oklch_to_hex(oklch):
    """Convert OKLCH tuple to a web-friendly hex string."""
    rgb = oklch_to_srgb(oklch)
    return "#{:02X}{:02X}{:02X}".format(*(int(c * 255) for c in rgb))


# -------------------- OKLCH → HEX converter (end)


# -------------------- Lightness adjuster (start)
def adjust_lightness(oklch, delta):
    """Lighten or darken an OKLCH color by ΔL (±)."""
    L, C, H = oklch
    return (np.clip(L + delta, 0, 1), C, H)


# -------------------- Lightness adjuster (end)


# -------------------- OKLCH blending helper (start)
def blend_oklch(color_a, color_b, t):
    """
    Interpolate smoothly between two OKLCH colors.
    t ∈ [0, 1] where 0 = color_a and 1 = color_b.
    Hue interpolation handles wrap-around correctly.
    """
    L1, C1, H1 = color_a
    L2, C2, H2 = color_b

    # shortest hue distance
    delta_h = (H2 - H1 + 180) % 360 - 180
    H = (H1 + t * delta_h) % 360

    L = L1 + t * (L2 - L1)
    C = C1 + t * (C2 - C1)

    return (L, C, H)


# -------------------- OKLCH blending helper (end)


# -------------------- Gradient generator (start)
def generate_gradient(color_a, color_b, steps=5, as_hex=True):
    """
    Produce a list of evenly spaced OKLCH or HEX colors.
    Example:
        generate_gradient((0.6,0.18,155), (0.8,0.20,20), 5)
    """
    stops = [blend_oklch(color_a, color_b, t) for t in np.linspace(0, 1, steps)]
    return [oklch_to_hex(c) for c in stops] if as_hex else stops


# -------------------- Gradient generator (end)


# -------------------- Preview helper (start)
def preview_gradient(color_a, color_b, steps=5):
    """
    Simple CLI preview printing hex values for debugging or theme tuning.
    """
    for h in generate_gradient(color_a, color_b, steps):
        print(h, end="  ")
    print()


# -------------------- Preview helper (end)


# -------------------- Self-test (start)
if __name__ == "__main__":
    c1 = (0.65, 0.18, 155)
    c2 = (0.75, 0.22, 20)

    print("Base 1:", oklch_to_hex(c1))
    print("Base 2:", oklch_to_hex(c2))
    print("Midpoint:", oklch_to_hex(blend_oklch(c1, c2, 0.5)))

    print("\nGradient preview:")
    preview_gradient(c1, c2, 7)
# -------------------- Self-test (end)
# -------------------- color_utils.py (end)
