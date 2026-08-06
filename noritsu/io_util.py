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
    """Load a raw scanner capture (NEF/DNG/ARW/CR2/...) as linear RGB via rawpy.

    Returns float32 (H,W,3) in ~[0,1] linear (no gamma, no camera WB, no
    auto-bright) — i.e. proportional to scene/negative transmittance.
    """
    import rawpy
    with rawpy.imread(str(path)) as raw:
        black = np.array(raw.black_level_per_channel[:3], dtype=np.float32)
        kw = dict(
            output_color=rawpy.ColorSpace.raw,
            output_bps=16,
            gamma=(1, 1),          # linear, no gamma
            no_auto_bright=True,
            use_camera_wb=False,   # keep raw channel response; WB handled later
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
        )
        # rawpy >= 0.20 supports use_black; subtract the black level ourselves
        # so the API stays compatible across rawpy versions.
        rgb = raw.postprocess(**kw)
    out = rgb.astype(np.float32)
    out = out - black[None, None, :]   # remove sensor black offset
    out = np.clip(out, 0, None)
    denom = 65535.0 - black[None, None, :]
    denom = np.where(denom > 0, denom, 1.0)
    out = out / denom
    return np.clip(out, 0, 1).astype(np.float32)


def _load_scanner_nef(path):
    """Load a Nikon Scan scanner NEF (Coolscan) from its RGB SubIFD.

    Scanner NEFs are TIFF-structured with the full-resolution processed RGB
    image in a SubIFD chain (tag 0x014A); camera NEFs carry a Bayer CFA mosaic
    there instead and must go through rawpy's demosaic path. Returns float32
    RGB (H,W,3) in [0,1], or None when this is not a scanner NEF.
    """
    try:
        import tifffile
    except ImportError:
        return None
    try:
        with tifffile.TiffFile(str(path)) as tif:
            best = None
            best_px = 0
            for sub in tif.pages[0].pages or []:
                tags = getattr(sub, "tags", None)
                if tags is None:
                    continue
                photo = tags.get("PhotometricInterpretation")
                comp = tags.get("Compression")
                spp = tags.get("SamplesPerPixel")
                photo_v = int(photo.value) if photo is not None else None
                spp_v = int(spp.value) if spp is not None else 1
                if photo_v == 32803:            # CFA mosaic
                    return None
                if comp is not None and int(comp.value) == 34713:  # Nikon NEF compression
                    return None
                if spp_v == 1 and sub.shape[0] * sub.shape[1] > 100_000:
                    return None                 # large single-channel plane: camera raw
                if photo_v == 2 and spp_v >= 3:
                    px = sub.shape[0] * sub.shape[1]
                    if px > best_px:
                        best, best_px = sub, px
            if best is None:
                return None
            arr = best.asarray()
    except Exception:
        return None
    if arr.ndim == 3 and arr.shape[2] > 3:
        arr = arr[:, :, :3]
    return _normalize(np.ascontiguousarray(arr), False)


RAW_EXTS = (".nef", ".dng", ".arw", ".cr2", ".cr3", ".arf", ".raf", ".orf", ".rw2")


def load_image(path, linearize_srgb=False):
    """Load an image and return float32 array in [0,1], shape (H,W,C) RGB.

    If the file is 16-bit, preserves full precision. Optionally applies
    sRGB EOTF (gamma decode) if the input is known to be sRGB-encoded.
    Headerless LS-600 `.RAW` dumps and Coolscan scanner NEFs are detected
    and decoded directly; camera raws still go through rawpy.
    """
    p = Path(path)
    if p.suffix.lower() == ".raw":
        from . import ls600raw
        bgr = ls600raw.load_ls600_raw(p)
        return np.ascontiguousarray(bgr[:, :, ::-1])  # sensor order is BGR
    if p.suffix.lower() == ".nef":
        img = _load_scanner_nef(p)
        if img is not None:
            return img
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
