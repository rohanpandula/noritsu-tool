#!/usr/bin/env python3
"""Ingestion tests: LS-600 RAW dimension detection and NEF routing.

Self-contained; builds every input synthetically. Covers:
- detect_dims tiers (exact, known-axis, blind factorization, ambiguity)
- load_ls600_raw channel order, 12/16-bit container sensing, size errors
- load_image routing: .RAW to the LS-600 decoder (BGR flipped to RGB),
  scanner NEFs to their RGB SubIFD, camera-style NEFs left for rawpy
"""
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from noritsu import io_util, ls600raw  # noqa: E402


def test_detect_dims():
    bpp = 6
    # tier 1: exact known frame
    assert ls600raw.detect_dims(4042 * 6391 * bpp) == (4042, 6391)
    # tier 2: known width, novel transport length
    assert ls600raw.detect_dims(4042 * 5000 * bpp) == (4042, 5000)
    # tier 2: known height, novel width
    assert ls600raw.detect_dims(3000 * 6391 * bpp) == (3000, 6391)
    # tier 3: unique factorization in-bounds (both prime)
    assert ls600raw.detect_dims(2003 * 3001 * bpp) == (2003, 3001)
    # ambiguous: 2400*4800 == 3200*3600, both plausible -> refuse to guess
    assert ls600raw.detect_dims(2400 * 4800 * bpp) is None
    # not a 3x uint16 raster at all
    assert ls600raw.detect_dims(4042 * 6391 * bpp + 1) is None
    assert ls600raw.detect_dims(0) is None
    print("detect_dims OK")


def test_load_raw(tmp):
    w, h = 50, 40
    bgr = np.zeros((h, w, 3), dtype="<u2")
    bgr[..., 0] = 4095   # B saturated
    bgr[..., 1] = 2048   # G mid
    bgr[..., 2] = 100    # R low
    p12 = tmp / "frame12.raw"
    bgr.tofile(p12)

    out = ls600raw.load_ls600_raw(p12, width=w, height=h)
    assert out.shape == (h, w, 3) and out.dtype == np.float32
    # container sensed as 12-bit: 4095 -> 1.0, channels stay BGR
    assert abs(out[0, 0, 0] - 1.0) < 1e-6
    assert abs(out[0, 0, 1] - 2048 / 4095) < 1e-6
    assert abs(out[0, 0, 2] - 100 / 4095) < 1e-6

    # a sample above 4095 flips the container to 16-bit
    b16 = bgr.copy()
    b16[0, 0, 1] = 60000
    p16 = tmp / "frame16.raw"
    b16.tofile(p16)
    out16 = ls600raw.load_ls600_raw(p16, width=w, height=h)
    assert abs(out16[0, 0, 1] - 60000 / 65535) < 1e-6
    assert abs(out16[0, 1, 1] - 2048 / 65535) < 1e-6

    # truncated file fails loudly, not with a garbled reshape
    (tmp / "short.raw").write_bytes(bgr.tobytes()[:1000])
    try:
        ls600raw.load_ls600_raw(tmp / "short.raw", width=w, height=h)
        raise AssertionError("short file should raise ValueError")
    except ValueError:
        pass

    # load_image routes .raw through the decoder, auto-detects the dims
    # (4042-wide tier-2 match here), and flips BGR -> RGB
    big = np.zeros((1000, 4042, 3), dtype="<u2")
    big[..., 0] = 4095
    big[..., 2] = 100
    pbig = tmp / "frame_auto.raw"
    big.tofile(pbig)
    img = io_util.load_image(pbig)
    assert img.shape == (1000, 4042, 3)
    assert abs(img[0, 0, 0] - 100 / 4095) < 1e-6   # R now first
    assert abs(img[0, 0, 2] - 1.0) < 1e-6          # B now last
    print("load_ls600_raw OK")


def test_nef_routing(tmp):
    import tifffile

    thumb = (np.linspace(0, 255, 12 * 16 * 3).reshape(12, 16, 3)).astype(np.uint8)
    full = np.zeros((64, 96, 3), dtype=np.uint16)
    full[..., 0] = 65535
    full[..., 1] = 32768
    full[..., 2] = 4096

    scanner = tmp / "scanner.nef"
    with tifffile.TiffWriter(scanner) as tw:
        tw.write(thumb, subifds=1, photometric="rgb")
        tw.write(full, photometric="rgb", subfiletype=0)
    img = io_util.load_image(scanner)
    assert img.shape == (64, 96, 3), "scanner NEF must load its RGB SubIFD, not the thumbnail"
    assert abs(img[0, 0, 0] - 1.0) < 1e-6
    assert abs(img[0, 0, 2] - 4096 / 65535) < 1e-6

    # camera-style NEF: large single-channel SubIFD (mosaic plane) -> not ours
    camera = tmp / "camera.nef"
    with tifffile.TiffWriter(camera) as tw:
        tw.write(thumb, subifds=1, photometric="rgb")
        tw.write(np.zeros((400, 300), dtype=np.uint16), photometric="minisblack", subfiletype=0)
    assert io_util._load_scanner_nef(camera) is None

    # no SubIFDs at all -> not ours either
    plain = tmp / "plain.nef"
    tifffile.imwrite(plain, full, photometric="rgb")
    assert io_util._load_scanner_nef(plain) is None
    print("NEF routing OK")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="noritsu_ingest_"))
    test_detect_dims()
    test_load_raw(tmp)
    test_nef_routing(tmp)
    print("ingest PASS")


if __name__ == "__main__":
    main()
