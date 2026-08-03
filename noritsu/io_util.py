"""Image I/O helpers: load/save 8/16-bit images as float32 in [0,1]."""
import numpy as np
from pathlib import Path
from PIL import Image


def _normalize(arr, linearize_srgb):
    if arr.dtype == np.uint8:
        out = arr.astype(np.float32) / 255.0
    elif arr.dtype == np.uint16:
        out = arr.astype(np.float32) / 65535.0
    elif arr.dtype in (np.uint32, np.int32):
        out = arr.astype(np.float32) / float(np.iinfo(arr.dtype).max)
    else:
        out = arr.astype(np.float32)
        if out.max() > 1.5:
            out = out / 65535.0
    if linearize_srgb:
        out = srgb_to_linear(out)
    return out


def _load_raw(path):
    """Load a raw scanner capture (NEF/DNG/CR2/...) as linear RGB via rawpy.

    Returns float32 (H,W,3) in ~[0,1] linear (no gamma, no camera WB, no
    auto-bright) — i.e. proportional to scene/negative transmittance.
    """
    import rawpy
    with rawpy.imread(str(path)) as raw:
        black = np.array(raw.black_level_per_channel[:3], dtype=np.float32)
        rgb = raw.postprocess(
            output_color=rawpy.ColorSpace.raw,
            output_bps=16,
            gamma=(1, 1),          # linear, no gamma
            no_auto_bright=True,
            use_camera_wb=False,   # keep raw channel response; WB handled later
            use_black=False,       # we subtract black ourselves
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
        )
    out = rgb.astype(np.float32)
    out = out - black[None, None, :]   # remove sensor black offset
    out = np.clip(out, 0, None)
    out = out / (65535.0 - black[None, None, :])
    return np.clip(out, 0, 1).astype(np.float32)


RAW_EXTS = (".nef", ".dng", ".cr2", ".cr3", ".arf", ".raf", ".orf", ".rw2")


def load_image(path, linearize_srgb=False):
    """Load an image and return float32 array in [0,1], shape (H,W,C) RGB.

    If the file is 16-bit, preserves full precision. Optionally applies
    sRGB EOTF (gamma decode) if the input is known to be sRGB-encoded.
    """
    p = Path(path)
    if p.suffix.lower() in RAW_EXTS:
        return _load_raw(p)
    if p.suffix.lower() in (".tif", ".tiff"):
        try:
            import tifffile
            arr = tifffile.imread(str(p))
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            return _normalize(arr, linearize_srgb)
        except Exception:
            pass
    im = Image.open(p)
    if im.mode not in ("RGB", "L", "I;16", "I", "RGB;16"):
        im = im.convert("RGB")
    arr = np.array(im)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    return _normalize(arr, linearize_srgb)


def save_image(path, arr, bits=16):
    """Save float32 [0,1] array as 8 or 16-bit image."""
    arr = np.clip(arr, 0.0, 1.0)
    p = Path(path)
    if bits == 16:
        data = (arr * 65535.0 + 0.5).astype(np.uint16)
    else:
        data = (arr * 255.0 + 0.5).astype(np.uint8)
    if p.suffix.lower() in (".tif", ".tiff") and bits == 16:
        import tifffile
        tifffile.imwrite(str(p), data, photometric="rgb")
    else:
        Image.fromarray(data, mode="RGB").save(p)


def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float32)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(v):
    v = np.asarray(v, dtype=np.float32)
    v = np.clip(v, 0.0, 1.0)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1.0 / 2.4) - 0.055)
