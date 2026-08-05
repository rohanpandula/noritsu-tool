"""CI smoke test: run the CLI end to end on a synthetic negative.

Covers the things that have actually broken before:
- a plain no-flag run completes (a dead-code --lab bug once crashed every run)
- --real-curve output differs from the default curve (it used to silently
  no-op when the vendor tables were missing from a clean clone)
- --lab runs
- the shipped per-stock calibration profiles load
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from noritsu import calibrate  # noqa: E402


def run_cli(neg_path, tmp, *flags):
    out = tmp / ("out_" + ("_".join(f.strip("-") for f in flags) or "plain") + ".tif")
    subprocess.run(
        [sys.executable, "-m", "noritsu.cli", str(neg_path), "-o", str(out), *flags],
        check=True,
        cwd=ROOT,
    )
    assert out.exists(), f"no output written for flags {flags}"
    return tifffile.imread(out)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="noritsu_ci_"))
    rng = np.random.default_rng(0)
    neg = (rng.random((64, 64, 3)) * 0.5 + 0.2).astype(np.float32)
    neg_path = tmp / "neg.tif"
    tifffile.imwrite(neg_path, (neg * 65535).astype("uint16"))

    plain = run_cli(neg_path, tmp)
    real = run_cli(neg_path, tmp, "--real-curve")
    run_cli(neg_path, tmp, "--lab")
    assert np.any(plain != real), "--real-curve was a no-op (base tone curve not loaded)"

    for stock in ("portra160", "portra400", "superia800"):
        c = calibrate.load_calib(ROOT / "noritsu" / "profiles" / f"{stock}_calib.npz")
        assert c["lut"].shape[0] == 3, f"bad LUT shape in {stock} profile"

    print("smoke PASS")


if __name__ == "__main__":
    main()
