#!/usr/bin/env python3
"""noritsu — Noritsu LS-600 style C-41 negative inversion CLI.

Usage:
    python -m noritsu.cli input.tif -o output.tif [options]

The input should be a LINEAR scan of a C-41 color negative (16-bit preferred).
If your scan is sRGB gamma-encoded (e.g. a flatbed JPEG/TIFF), pass --srgb-input.
"""
import argparse
import sys

import numpy as np

from . import io_util, pipeline


def parse_gains(s):
    if s is None:
        return (1.0, 1.0, 1.0)
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 3:
        raise SystemExit("--wb expects R,G,B e.g. 1.0,1.0,1.12")
    return tuple(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="noritsu",
        description="Noritsu LS-600 style C-41 negative inversion.",
    )
    ap.add_argument("input", help="input negative image (TIFF/PNG/JPG)")
    ap.add_argument("-o", "--output", required=True, help="output positive image")
    ap.add_argument("--bits", type=int, default=16, choices=[8, 16],
                    help="output bit depth (default 16)")
    ap.add_argument("--preview", action="store_true",
                    help="also write an 8-bit JPEG preview for quick checking")
    ap.add_argument("--no-crop", action="store_true",
                    help="don't auto-crop to the film area (keep clear margins)")
    ap.add_argument("--srgb-input", action="store_true",
                    help="input is sRGB gamma-encoded; linearize it first")
    ap.add_argument("--black", type=float, default=0.0,
                    help="scanner black level to subtract, 0..1 (default 0)")

    g = ap.add_argument_group("inversion")
    g.add_argument("--dmin", type=float, nargs=3, metavar=("R", "G", "B"),
                   help="override film-base density (Dmin) per channel")
    g.add_argument("--dmax", type=float, nargs=3, metavar=("R", "G", "B"),
                   help="override max density (Dmax) per channel")
    g.add_argument("--dmin-pct", type=float, default=0.5,
                   help="percentile for auto Dmin (default 0.5)")
    g.add_argument("--dmax-pct", type=float, default=99.8,
                   help="percentile for auto Dmax (default 99.8)")
    g.add_argument("--no-border", action="store_true",
                   help="don't use the film rebate/border for Dmin (use percentile)")

    r = ap.add_argument_group("render")
    r.add_argument("--contrast", type=float, default=1.05, help="tone contrast")
    r.add_argument("--toe", type=float, default=0.02, help="shadow lift")
    r.add_argument("--gamma", type=float, default=0.98, help="midtone gamma")
    r.add_argument("--sat", "--saturation", dest="saturation", type=float,
                   default=1.0, help="saturation multiplier")
    r.add_argument("--wb", type=str, default=None,
                   help="manual white balance gains R,G,B")
    r.add_argument("--no-auto-wb", action="store_true",
                   help="disable automatic white balance")
    r.add_argument("--real-curve", action="store_true",
                   help="use the real Noritsu tone curve extracted from "
                        "CommonCalcPara.Dat (experimental; best with linear input)")
    r.add_argument("--calib", type=str, default=None,
                   help="calibration .npz (from noritsu.calibrate) to match a "
                        "reference rendering (e.g. NLP Noritsu or a lab scan)")
    r.add_argument("--stock", type=str, default=None,
                   choices=["portra160", "portra400", "superia800"],
                   help="auto-select a per-stock calibration profile (from real LS-600 pairs)")

    args = ap.parse_args(argv)

    import os
    if os.path.isdir(args.input):
        return run_batch(args)
    return run_one(args.input, args.output, args)


EXTS = (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".dng", ".nef")


def run_batch(args):
    import os
    os.makedirs(args.output, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(args.input)):
        if name.lower().endswith(EXTS):
            in_p = os.path.join(args.input, name)
            base = os.path.splitext(name)[0]
            out_p = os.path.join(args.output, base + (".tif" if args.bits == 16 else ".png"))
            run_one(in_p, out_p, args, quiet=True)
            n += 1
    print(f"processed {n} file(s) -> {args.output}")
    return 0


def run_one(in_path, out_path, args, quiet=False):
    img = io_util.load_image(in_path, linearize_srgb=args.srgb_input)

    calib = None
    if args.calib:
        from . import calibrate as calibmod
        calib = calibmod.load_calib(args.calib)
    elif args.stock:
        from . import calibrate as calibmod
        import os
        profile_path = os.path.join(os.path.dirname(__file__), "profiles", f"{args.stock}_calib.npz")
        if os.path.exists(profile_path):
            calib = calibmod.load_calib(profile_path)
        elif not quiet:
            print(f"  warning: no profile for {args.stock}, continuing without calibration")

    out, meta, wb = pipeline.process_negative(
        img,
        black=args.black,
        dmin=args.dmin,
        dmax=args.dmax,
        dmin_percentile=args.dmin_pct,
        dmax_percentile=args.dmax_pct,
        use_border=not args.no_border,
        tone_contrast=args.contrast,
        tone_toe=args.toe,
        tone_gamma=args.gamma,
        wb_gains=parse_gains(args.wb),
        saturation=args.saturation,
        auto_wb=not args.no_auto_wb,
        real_curve=args.real_curve,
        calib=calib,
        crop=not args.no_crop,
    )

    io_util.save_image(out_path, out, bits=args.bits)

    if args.preview:
        prev = out_path.rsplit(".", 1)[0] + "_preview.jpg"
        io_util.save_image(prev, out, bits=8)

    dmin = meta["dmin"]
    dmax = meta["dmax"]
    if not quiet:
        print(f"wrote {out_path}")
        print(f"  Dmin (mask)  R={dmin[0]:.3f} G={dmin[1]:.3f} B={dmin[2]:.3f}")
        print(f"  Dmax         R={dmax[0]:.3f} G={dmax[1]:.3f} B={dmax[2]:.3f}")
        print(f"  WB gains     R={wb[0]:.3f} G={wb[1]:.3f} B={wb[2]:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
