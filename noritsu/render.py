"""Noritsu-style rendering: tone curve + color correction.

Noritsu builds its tone curves from control points (pcb_MakeGammaCurve2 uses
20 points across shadow/mid/highlight regions) and applies contrast via slope
integration (MakeContrastLut). Here we provide equivalent smooth curves that
reproduce the characteristic Noritsu print/film-scan tonality, plus the color
correction stages (white balance, saturation, gentle hue protection).
"""
import numpy as np


def gamma_curve(x, gamma):
    """Simple power curve. x in [0,1]."""
    return np.clip(x, 0.0, 1.0) ** gamma


def spline_interp(xp, fp, x):
    """Monotone piecewise interpolation of control points (xp,fp) at x."""
    return np.interp(x, xp, fp)


def noritsu_tone_curve(x, contrast=1.0, toe=0.0, gamma=1.0):
    """A Noritsu-flavored S-curve.

    The Noritsu look has a slightly lifted toe, a long straight-line section,
    and a soft shoulder (classic negative/print characteristic curve). We build
    it from control points like pcb_MakeGammaCurve2 does.

    contrast: >1 punchier, <1 flatter.
    toe: shadow lift amount.
    gamma: overall midtone gamma applied after the S-curve.
    """
    x = np.clip(x, 0.0, 1.0)
    # control points (input density-normalized -> output)
    # gentle S: compress toe and shoulder, boost midtone slope by `contrast`
    k = contrast
    pts_x = np.array([0.0, 0.08, 0.25, 0.5, 0.75, 0.92, 1.0], dtype=np.float32)
    # build output with an S shape; midpoint stays ~0.5
    mid = 0.5
    pts_y = mid + (pts_x - mid) * k
    # toe lift
    pts_y = pts_y + toe * (1.0 - pts_x) * np.exp(-pts_x * 4.0)
    pts_y = np.clip(pts_y, 0.0, 1.0)
    # enforce monotonic
    for i in range(1, len(pts_y)):
        if pts_y[i] < pts_y[i - 1]:
            pts_y[i] = pts_y[i - 1]
    out = np.interp(x, pts_x, pts_y)
    if gamma != 1.0:
        out = out ** gamma
    return out.astype(np.float32)


def white_balance(img, gains):
    """Apply per-channel multiplicative white-balance gains (R,G,B)."""
    g = np.asarray(gains, dtype=np.float32).reshape(1, 1, 3)
    return np.clip(img * g, 0.0, 1.0)


def to_ycbcr_like(img):
    """Convert RGB->YCbCr-ish (BT.601) for saturation/hue work."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = (b - y) * 0.564 + 0.0
    cr = (r - y) * 0.713 + 0.0
    return y, cb, cr


def from_ycbcr_like(y, cb, cr):
    b = y + cb / 0.564
    r = y + cr / 0.713
    g = (y - 0.299 * r - 0.114 * b) / 0.587
    return np.stack([r, g, b], axis=-1)


def adjust_saturation(img, sat):
    """Adjust saturation around luma. sat=1 neutral."""
    y, cb, cr = to_ycbcr_like(img)
    cb *= sat
    cr *= sat
    out = from_ycbcr_like(y, cb, cr)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def render(
    positive,
    tone_contrast=1.05,
    tone_toe=0.02,
    tone_gamma=0.98,
    wb_gains=(1.0, 1.0, 1.0),
    saturation=1.0,
    apply_curve=True,
    lut=None,
):
    """Apply the Noritsu-style render to a density-normalized positive [0,1].

    lut: optional 1-D tone LUT (list/array in [0,1]) to use instead of the
    synthetic S-curve (e.g. the real Noritsu curve from tables.tone_curve_lut()).
    """
    out = positive
    # white balance first (in linear density-normalized space)
    if any(abs(g - 1.0) > 1e-4 for g in wb_gains):
        out = white_balance(out, wb_gains)
    # tone curve per channel
    if apply_curve:
        if lut is not None:
            arr = np.asarray(lut, dtype=np.float32)
            idx = np.clip(out, 0, 1) * (arr.size - 1)
            i0 = np.floor(idx).astype(int)
            i1 = np.minimum(i0 + 1, arr.size - 1)
            t = (idx - i0).astype(np.float32)
            out = arr[i0] * (1 - t) + arr[i1] * t
        else:
            f = lambda v: noritsu_tone_curve(v, tone_contrast, tone_toe, tone_gamma)
            out = np.stack([f(out[..., c]) for c in range(3)], axis=-1)
    # saturation
    if abs(saturation - 1.0) > 1e-4:
        out = adjust_saturation(out, saturation)
    return np.clip(out, 0.0, 1.0).astype(np.float32)
