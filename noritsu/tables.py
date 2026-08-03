"""Load real Noritsu data tables extracted from the EZ Controller .dat files.

The .dat files are raw C-struct dumps. We extract the fields we have decoded:
- CommonCalcPara.Dat: 20-point base tone curve (u32, 0..65535) at offset 0.

More fields can be added as the struct layout is recovered (see ../re/RE_NOTES.md).
"""
import os
import struct
from functools import lru_cache

# Default location of the extracted tables (overridable via env NORITSU_TABLES)
_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "re", "imgproc", "ImageDataProc", "Data", "CorrectServ",
)


def tables_dir():
    return os.environ.get("NORITSU_TABLES", _DEFAULT)


def _para_dir(group="IQGrp000", variant="00000005"):
    return os.path.join(tables_dir(), group, variant, "PCB_PARA")


@lru_cache(maxsize=None)
def load_base_tone_curve():
    """Return the real Noritsu 20-point base tone curve normalized to [0,1].

    Read from CommonCalcPara.Dat (first 20 u32, values 0..65535).
    Interpreted as output value at evenly-spaced input i/19.
    """
    p = os.path.join(_para_dir(), "CommonCalcPara.Dat")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        data = f.read()
    u32 = struct.unpack("<20I", data[:80])
    return [v / 65535.0 for v in u32]


def tone_curve_lut(n=4096):
    """Build an n-entry LUT from the real base tone curve (linear interp).

    Returns list of n floats in [0,1], or None if tables unavailable.
    """
    curve = load_base_tone_curve()
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
