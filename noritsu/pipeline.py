"""End-to-end Noritsu-style C-41 negative -> positive pipeline."""
import numpy as np

from . import invert, render, io_util, tables, calibrate as calibmod


def process_negative(
    img_linear,
    black=0.0,
    dmin=None,
    dmax=None,
    dmin_percentile=0.5,
    dmax_percentile=99.95,
    tone_contrast=1.05,
    tone_toe=0.02,
    tone_gamma=0.98,
    wb_gains=(1.0, 1.0, 1.0),
    saturation=1.0,
    auto_wb=True,
    real_curve=False,
    use_border=True,
    calib=None,
    crop=True,
):
    """Full pipeline: linear negative scan -> rendered positive (both [0,1]).

    img_linear: (H,W,3) float32 linear transmittance of the negative.
    calib: optional calibration dict (from calibrate.load_calib) whose per-channel
           LUT maps the density-normalized positive to a reference rendering;
           when given it replaces WB + tone curve (it already encodes them).
    """
    if crop:
        img_linear, bbox = invert.crop_to_film(img_linear)

    positive, meta = invert.invert_negative(
        img_linear,
        black=black,
        dmin=dmin,
        dmax=dmax,
        dmin_percentile=dmin_percentile,
        dmax_percentile=dmax_percentile,
        use_border=use_border,
    )

    if calib is not None:
        out = calibmod.apply_calib(positive, calib)
        if abs(saturation - 1.0) > 1e-4:
            out = render.adjust_saturation(out, saturation)
        return out, meta, (1.0, 1.0, 1.0)

    if auto_wb and wb_gains == (1.0, 1.0, 1.0):
        # Neutralize the residual color cast of the inverted positive so that the
        # average scene renders neutral (Noritsu's auto white balance target).
        mean = positive.reshape(-1, 3).mean(axis=0)
        mean = np.clip(mean, 1e-4, None)
        target = mean.mean()
        wb_gains = tuple(float(target / mean[c]) for c in range(3))

    out = render.render(
        positive,
        tone_contrast=tone_contrast,
        tone_toe=tone_toe,
        tone_gamma=tone_gamma,
        wb_gains=wb_gains,
        saturation=saturation,
        lut=tables.tone_curve_lut() if real_curve else None,
    )
    return out, meta, wb_gains
