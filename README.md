# noritsu — C-41 negative processing in the Noritsu "look"

A CLI that inverts C-41 color negative scans in **density space** — the way
Noritsu LS-600 and Frontier minilab scanners do — and renders a positive with a
Noritsu-flavored tone curve and color correction. Built from a
reverse-engineering study of the actual Noritsu LS-600 / EZ Controller 6.5
software (no scanner required).

```
python -m noritsu.cli scan_of_negative.tif -o positive.tif
```

## Why this exists

The Noritsu LS-600 is a professional film minilab scanner whose output has a
beloved, distinctive "look". People chase it with presets and plug-ins. This
project goes one level deeper: it reads the actual ImgDataProc ("RD5X") engine
binaries and correction tables from the LS-600 software stack, recovers the
physics and the tone curves, then reimplements the conversion as a small,
inspectable Python tool.

The inversion principle (confirmed from the engine):

> A scanner measures **transmittance**. A color negative's dyes are
> complementary (C/M/Y) under an orange mask. Convert to density
> `D = −log10(transmittance)`, remove the per-channel mask (Dmin), and
> normalize by the density range. Density conversion inherently resolves both
> the tonal **and** the complementary-color inversion in one
> physically-correct step.

## Install

Requires Python 3.10+, `numpy`, `Pillow`, and `tifffile` (for 16-bit TIFF):

```
pip install numpy pillow tifffile
```

## Usage

```
python -m noritsu.cli scan_of_negative.tif -o positive.tif
```

Common options:

| Option | Meaning |
| --- | --- |
| `--srgb-input` | your scan is sRGB-encoded (DSLR JPEG/flatbed): linearize it first |
| `--black 0.02` | subtract a scanner black level (0..1) |
| `--contrast 1.08` | tone-curve contrast |
| `--sat 1.05` | saturation multiplier |
| `--gamma 0.98` | midtone gamma |
| `--wb R,G,B` | manual white-balance gains (else auto-neutralize) |
| `--no-auto-wb` | disable auto white balance |
| `--dmin R G B` | override film-base density (advanced) |
| `--dmax R G B` | override max density (advanced) |
| `--bits 8\|16` | output bit depth (default 16) |

### Getting the best result

* **Feed it linear data.** The inversion assumes pixel value ∝ transmittance.
  If you shot the negative with a DSLR, develop the RAW linearly (no profile,
  no gamma). If you have a flatbed/JPEG scan, pass `--srgb-input`.
* **Include the film border** (or unexposed rebate) so Dmin can be estimated,
  or pass `--dmin` manually.
* Start with defaults, then tune `--contrast` and `--sat`.

### Pipeline

1. linearize input (optional sRGB EOTF)
2. transmittance → density, per channel
3. estimate/remove Dmin (orange mask), normalize by Dmax − Dmin
4. auto white balance (neutralize residual cast)
5. Noritsu-style tone curve (control-point S-curve, per channel)
6. saturation adjustment
7. write 16-bit positive

## Fidelity

The inversion math is validated by a round-trip test (`test_roundtrip.py`,
~0.4% mean error); `calibrate.py` can fit the render to any reference output at
~0.12% error. The tone curve and color stages are a faithful approximation of
the Noritsu rendering, recovered from the engine's `CommonCalcPara` tone-curve
tables and `SpecialPcb` per-film tables.

See `samples/compare.jpg` for a side-by-side.

## Documentation

* `docs/JOURNEY.md` — the full chronological story of the reverse-engineering
  work: unpacking the installers, mapping the pipeline, decoding the `.dat`
  tables, the density inversion, driving the real engine headless, and the
  CF-format / validation-gate work.
* `docs/BLOG_POST.md` — a tighter, written-up version of the same story, and
  how this differs from preset-based "Noritsu look" tools.
* `docs/RD5X_INPUT_FORMATS.md` — the recovered film raster ABIs.
* `docs/RD5X_XML_SCHEMA.md` — the engine's XML command schema.

## How this differs from a preset

Negative Lab Pro and similar tools ship a *tuned approximation* of the look
(Lightroom grading tweaks over a proprietary camera profile). This project's
model is reconstructed from the **actual shipped Noritsu assets** — the
`SpecialPcb` per-film gamma/contrast/white-balance tables, the `CommonCalcPara`
tone curve, and the engine's density-domain pipeline. It is physically
grounded, inspectable (open a table and see the curve), and calibratable to any
reference render. It does **not** claim byte-identical LS-600 output (your
scanner's spectral response and a unit's per-unit calibration differ).

## License

MIT. The reverse-engineering was done from public installer binaries for
research/compatibility purposes; no Noritsu source code, firmware, or vendor
binaries are distributed here — only the format knowledge recovered from them
and this original implementation.
