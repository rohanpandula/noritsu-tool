"""Calibrate the render against a reference (negative + target positive).

If you ever obtain a (C-41 negative, Noritsu output) pair, this fits a
per-channel tone LUT (via percentile pairing) so the CLI reproduces the
reference's rendering. This is the highest-value lever toward "byte-perfect"
without the hardware.

Usage (module):
    python -m noritsu.calibrate neg.tif target.tif -o calib.npz
Then run the CLI with --calib calib.npz.
"""
import argparse

import numpy as np

from . import invert, io_util

N_POINTS = 1024


def fit_lut(src, dst, n=N_POINTS):
    """Per-channel mapping src->dst using PIXEL CORRESPONDENCE.

    src, dst: (N,3) aligned samples in [0,1]. For each channel, bin src into n
    bins and take the mean dst per bin (the true per-channel transfer), filling
    empty bins by interpolation. Returns (3, n) LUT for evenly spaced src inputs.
    """
    lut = np.zeros((3, n), dtype=np.float32)
    for c in range(3):
        s = np.clip(src[:, c], 0, 1)
        d = np.clip(dst[:, c], 0, 1)
        idx = np.clip((s * (n - 1)).astype(int), 0, n - 1)
        sums = np.zeros(n, dtype=np.float64)
        cnts = np.zeros(n, dtype=np.float64)
        np.add.at(sums, idx, d)
        np.add.at(cnts, idx, 1)
        valid = cnts > 0
        xs = np.where(valid, sums / np.maximum(cnts, 1), np.nan)
        # interpolate over empty bins
        good = np.where(valid)[0]
        if good.size == 0:
            lut[c] = np.linspace(0, 1, n)
            continue
        lut[c] = np.interp(np.arange(n), good, xs[good])
    return lut


def calibrate(neg_linear, target, use_border=True):
    """Return a calibration dict {lut:(3,n), wb:(3,)} mapping pipeline positive
    (density-normalized) to the target's rendering."""
    positive, meta = invert.invert_negative(neg_linear, use_border=use_border)
    # target as float [0,1]
    t = np.clip(target, 0, 1)
    h = min(positive.shape[0], t.shape[0])
    w = min(positive.shape[1], t.shape[1])
    p = positive[:h, :w].reshape(-1, 3)
    d = t[:h, :w].reshape(-1, 3)
    lut = fit_lut(p, d)
    return {"lut": lut, "dmin": meta["dmin"], "dmax": meta["dmax"]}


def save_calib(calib, path):
    np.savez_compressed(path, lut=calib["lut"], dmin=calib["dmin"], dmax=calib["dmax"])


def load_calib(path):
    z = np.load(path)
    return {"lut": z["lut"], "dmin": z["dmin"], "dmax": z["dmax"]}


def apply_calib(positive, calib):
    """Apply a calibrated per-channel LUT to a density-normalized positive."""
    lut = calib["lut"]  # (3, n)
    n = lut.shape[1]
    out = np.empty_like(positive)
    for c in range(3):
        x = np.clip(positive[..., c], 0, 1) * (n - 1)
        i0 = np.floor(x).astype(int)
        i1 = np.minimum(i0 + 1, n - 1)
        t = (x - i0).astype(np.float32)
        out[..., c] = lut[c][i0] * (1 - t) + lut[c][i1] * t
    return np.clip(out, 0, 1).astype(np.float32)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="noritsu-calibrate",
                                 description="Fit tone LUT from neg+target pair.")
    ap.add_argument("negative")
    ap.add_argument("target")
    ap.add_argument("-o", "--output", required=True, help="output .npz")
    ap.add_argument("--srgb-input", action="store_true")
    ap.add_argument("--srgb-target", action="store_true", default=True)
    args = ap.parse_args(argv)

    neg = io_util.load_image(args.negative, linearize_srgb=args.srgb_input)
    tgt = io_util.load_image(args.target, linearize_srgb=False)  # target is a display image
    calib = calibrate(neg, tgt)
    save_calib(calib, args.output)
    print(f"wrote {args.output} (lut {calib['lut'].shape})")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
