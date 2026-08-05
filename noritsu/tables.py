"""Load real Noritsu data tables extracted from the EZ Controller .dat files.

The .dat files are raw C-struct dumps. We extract the fields we have decoded:
- CommonCalcPara.Dat: 20-point base tone curve (u32, 0..65535) at offset 0.

The vendor .dat files are NOT distributed with this repo. The extracted numbers
live in ``tables/base_tone_curve.json`` so a clean clone works out of the box.
If you have the real EZ Controller data tree, point ``NORITSU_TABLES`` at its
``CorrectServ`` directory and the .dat files are read directly instead.

More fields can be added as the struct layout is recovered.
"""
import json
import os
import struct
from functools import lru_cache

_HERE = os.path.dirname(os.path.abspath(__file__))

# Derived curves shipped with the package (no vendor binaries).
_CURVE_JSON = os.path.join(_HERE, "tables", "base_tone_curve.json")

DEFAULT_VARIANT = "00000005"


def tables_dir():
    """Directory of a real EZ Controller ``CorrectServ`` tree, if you have one.

    Set via the ``NORITSU_TABLES`` env var. There is no default — without it,
    the derived JSON shipped in ``tables/`` is used.
    """
    return os.environ.get("NORITSU_TABLES")


@lru_cache(maxsize=None)
def _shipped_curves():
    """Return the derived curve doc, or None if the JSON is missing."""
    if not os.path.exists(_CURVE_JSON):
        return None
    with open(_CURVE_JSON) as f:
        return json.load(f)


def available_variants():
    """Variant ids we ship a base curve for (e.g. '00000005')."""
    doc = _shipped_curves()
    return sorted(doc["variants"]) if doc else []


@lru_cache(maxsize=None)
def load_base_tone_curve(variant=DEFAULT_VARIANT):
    """Return the real Noritsu 20-point base tone curve normalized to [0,1].

    20 u32 at offset 0 of CommonCalcPara.Dat, read as the output value at
    evenly-spaced inputs i/19. Prefers the real .dat when NORITSU_TABLES points
    at an EZ Controller CorrectServ tree; otherwise uses the derived JSON
    shipped here. Returns None if neither source is available.

    Curves are identical across IQGrp000 and IQGrp001; only the variant matters.
    Variant 00000000 is a linear ramp (i.e. a no-op curve).
    """
    u32 = None
    td = tables_dir()
    if td:
        p = os.path.join(td, "IQGrp000", variant, "PCB_PARA", "CommonCalcPara.Dat")
        if os.path.exists(p):
            with open(p, "rb") as f:
                u32 = struct.unpack("<20I", f.read(80))
    if u32 is None:
        doc = _shipped_curves()
        if doc is None or variant not in doc["variants"]:
            return None
        u32 = doc["variants"][variant]
    scale = float((_shipped_curves() or {}).get("_scale", 65535))
    # a couple of variants overshoot full scale by <0.4%; clamp, it's a
    # display transfer curve and >1 output is meaningless downstream
    return [min(1.0, max(0.0, v / scale)) for v in u32]


def tone_curve_lut(n=4096, variant=DEFAULT_VARIANT):
    """Build an n-entry LUT from the real base tone curve (linear interp).

    Returns list of n floats in [0,1], or None if tables unavailable.
    """
    curve = load_base_tone_curve(variant)
    if curve is None:
        return None
    m = len(curve)
    lut = []
    for i in range(n):
        x = i / (n - 1) * (m - 1)
        i0 = int(x)
        i1 = min(i0 + 1, m - 1)
        t = x - i0
        lut.append(curve[i0] * (1 - t) + curve[i1] * t)
    return lut
