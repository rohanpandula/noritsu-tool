"""Load Noritsu LS-600 'FULL...RAW' scan frames.

Recovered layout (from two LS-600 RAW samples provided by an LS-600 owner):
- Headerless raster of 3 x uint16 LE per pixel (B, G, R slots).
- 12-bit scanner data (0..4095) stored in the low bits.
- Width x Height = 4042 x 6391 for the 'FULL' frames we have.
Returns float32 (H, W, 3) in [0,1], channels BGR, linear (no gamma, no WB).
"""
import numpy as np


WIDTH = 4042
HEIGHT = 6391


def load_ls600_raw(path, width=WIDTH, height=HEIGHT, maxv=4095.0):
    d = np.fromfile(path, dtype=np.uint16).astype(np.float32)
    px = d.size // 3
    arr = d[: px * 3].reshape(-1, 3)
    arr = arr[: width * height].reshape(height, width, 3)
    return np.clip(arr / maxv, 0, 1).astype(np.float32)

# --- LS-600 machine geometry transform ---
# Verified empirically against real machine TIFFs (2026-08-04).
# The LS-600 crops the 6391x4042 portrait raw (BGR, 12-bit) to a sub-rect
# then resamples to 6048x4011 output. Derivation from TrzCorFile UsImRct:
#   THUM (252x399) UsImRct=(1,10,251,388) => crop 250x378
#   THUM is ~1/16 downsampled FULL: y0=16, x0=168, h=4008, w=6048
#   Final resize 4008x6048 -> 4011x6048 (INTER_AREA)
CROP_Y0 = 16
CROP_X0 = 168
CROP_H = 4008
CROP_W = 6048
TIF_H = 4011
TIF_W = 6048


def align_to_machine(linear_bgr):
    """Crop + resize a landscape-oriented LS-600 raw to match machine TIF geometry.

    Args:
        linear_bgr: (H,W,3) float32 BGR landscape raw after np.rot90(raw, 3).

    Returns:
        (4011, 6048, 3) float32 BGR array, spatially aligned to machine output.
    """
    import cv2
    cropped = linear_bgr[CROP_Y0:CROP_Y0 + CROP_H, CROP_X0:CROP_X0 + CROP_W, :]
    return cv2.resize(cropped, (TIF_W, TIF_H), interpolation=cv2.INTER_AREA).astype(np.float32)
