#!/usr/bin/env python3
"""Round-trip test: positive -> simulated C-41 negative -> pipeline -> positive.

Validates the density inversion end-to-end without needing a real scanner or
any external image files. Self-contained; safe to run anywhere.
"""
import numpy as np
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from noritsu import io_util, pipeline

# realistic C-41 film base + fog (orange mask): blue absorbed most
DMIN = np.array([0.20, 0.35, 0.60], dtype=np.float32)   # R,G,B density
RANGE = np.array([2.30, 2.30, 2.30], dtype=np.float32)   # density range per ch


def make_scene(w=128, h=96):
    """A synthetic 'scene' image: smooth color gradients + structured detail."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = (xx / w)
    g = (yy / h)
    b = 0.5 + 0.5 * np.sin(4 * np.pi * xx / w) * np.cos(4 * np.pi * yy / h)
    scene = np.stack([r, g, b], axis=-1)
    rng = np.random.default_rng(7)
    scene = np.clip(scene + rng.normal(0, 0.02, scene.shape), 0.0, 1.0)
    return scene.astype(np.float32)


def simulate_negative(positive_linear):
    """positive scene [0,1] -> linear transmittance scan of the C-41 negative."""
    D = DMIN[None, None, :] + RANGE[None, None, :] * positive_linear
    T = np.power(10.0, -D)
    return T.astype(np.float32)


def main():
    outdir = Path(tempfile.mkdtemp(prefix="noritsu_roundtrip_"))
    pos = make_scene()
    print("scene:", pos.shape, pos.dtype, "dtype range:", pos.min(), pos.max())

    neg_scan = simulate_negative(pos)
    io_util.save_image(str(outdir / "sim_negative.tif"), neg_scan, bits=16)

    out, meta, wb = pipeline.process_negative(
        neg_scan,
        dmin_percentile=0.5,
        dmax_percentile=99.9,
        tone_contrast=1.0,   # flat for round-trip fidelity check
        tone_toe=0.0,
        tone_gamma=1.0,
        saturation=1.0,
        auto_wb=False,
    )
    io_util.save_image(str(outdir / "roundtrip_out.tif"), out, bits=16)

    err = np.abs(out - pos)
    print("Dmin est:", meta["dmin"], " true:", DMIN)
    print("Dmax est:", meta["dmax"], " true:", DMIN + RANGE)
    print("mean abs error vs original: %.4f" % err.mean())
    print("95th pct abs error:         %.4f" % np.percentile(err, 95))
    print("outputs written to:", outdir)
    # regression gates (typical values: mean 0.0002, p95 0.0011)
    assert err.mean() < 0.005, "roundtrip mean error too high: %.4f" % err.mean()
    assert np.percentile(err, 95) < 0.02, "roundtrip p95 error too high"
    print("PASS")


if __name__ == "__main__":
    main()
