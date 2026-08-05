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

Point the input at a **directory** instead of a file and every image inside is
batch-processed into the `-o` directory:

```
python -m noritsu.cli ./negatives/ -o ./positives/
```

### The options you actually reach for

| Option | Meaning |
| --- | --- |
| `--srgb-input` | your scan is sRGB-encoded (DSLR JPEG/flatbed): linearize it first |
| `--stock portra160` | use a per-stock profile fitted from real LS-600 pairs |
| `--lab` | gentler, print-ready rendering (see [Lab mode](#lab-mode)) |
| `--contrast 1.08` | tone-curve contrast |
| `--gamma 0.8` | midtone gamma — *lower* lifts a thin negative |
| `--preview` | also write an 8-bit JPEG beside the output for a quick look |

### Full option reference

**Input and output**

| Option | Default | Meaning |
| --- | --- | --- |
| `input` | *required* | negative image, or a directory to batch-process |
| `-o`, `--output` | *required* | output positive, or output directory in batch mode |
| `--bits 8\|16` | `16` | output bit depth |
| `--preview` | off | also write an 8-bit JPEG preview beside the output |
| `--srgb-input` | off | input is sRGB gamma-encoded; linearize before inverting |
| `--black 0.02` | `0.0` | scanner black level to subtract (0..1) |
| `--no-crop` | off | keep the clear margins instead of auto-cropping to the film area |

**Inversion** — finding the orange mask and the density range

| Option | Default | Meaning |
| --- | --- | --- |
| `--dmin R G B` | auto | override film-base density (the mask) per channel |
| `--dmax R G B` | auto | override maximum density per channel |
| `--dmin-pct` | `0.5` | percentile used for auto Dmin |
| `--dmax-pct` | `99.8` | percentile used for auto Dmax — drop to `98.0` for a thin negative |
| `--no-border` | off | ignore the film rebate when estimating Dmin; use the percentile instead |

**Render** — tone and color

| Option | Default | Meaning |
| --- | --- | --- |
| `--contrast` | `1.05` | tone-curve contrast |
| `--gamma` | `0.98` | midtone gamma (lower is brighter on a thin negative) |
| `--toe` | `0.02` | shadow lift |
| `--sat`, `--saturation` | `1.0` | saturation multiplier |
| `--wb R,G,B` | auto | manual white-balance gains |
| `--no-auto-wb` | off | disable automatic white balance |
| `--real-curve` | off | use the real Noritsu tone curve from `CommonCalcPara.Dat` (experimental; best with linear input) |
| `--calib FILE.npz` | none | fit to your own reference render (see `noritsu/calibrate.py`) |
| `--stock NAME` | none | per-stock profile: `portra160`, `portra400`, `superia800` |
| `--lab` | off | lab-tech rendering; implies `--real-curve` |

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

## Fidelity — how close to a real LS-600?

The inversion math is validated by a round-trip test (`test_roundtrip.py`,
~0.4% mean error). The tone curve and color stages are a faithful approximation
of the Noritsu rendering, recovered from the engine's `CommonCalcPara`
tone-curve tables and `SpecialPcb` per-film tables.

**Validated against a real LS-600** (2026): an LS-600 owner provided raw scan
frames (`FULL*.RAW`, headerless 3×uint16 BGR, 12-bit, 4042×6391), the
machine's own processed 16-bit positives, and the real per-frame Correction
Files (`.prm`, 0x504E8 bytes). That confirmed the recovered CF format
field-for-field (checksum = signed-byte sum of the tail at u32[0], size,
CorrParamHead=5, `NKC-ICCS` magic, SrcImg path), and the exact geometric
crop+resample (UsImRct from TrzCorFile → `align_to_machine()`).

After calibration, this is how close our pipeline gets to the machine's own
output (per-pixel normalized cross-correlation on 27 frames across 3 stocks):

| Stock | ICE | Frames | Mean NCC | Min NCC | Mean RMS(/255) |
|---|---|---|---|---|---|
| **Portra 400** | off | 3 | **0.940** | 0.926 | 27.6 |
| **Portra 160** | on | 6 | **0.936** | 0.904 | 27.5 |
| **Superia 800** | off | 12 | **0.881** | 0.838 | 40.7 |

The Portra numbers are tight — ~94% pixel correlation. Superia 800 is lower
because the LS-600 internally uses per-film adjustments (its `SpecialPcb`
tables) for different emulsions that our generic curve doesn't include. The
per-stock calibration profile helps, but the actual `SpecialPcb` tables would
close the rest.

**Visually**, the output is excellent on all stocks — "oh fuck yeah these are
so good" (actual user quote). The gap is academic: per-frame density estimation
variation plus missing per-film tables. It does not affect the practical result.

### Per-stock calibration profiles

The repo ships per-stock profiles fitted from real LS-600 raw/TIFF pairs:

```
python -m noritsu.cli scan.tif -o out.tif --stock portra160
python -m noritsu.cli scan.tif -o out.tif --stock portra400
python -m noritsu.cli scan.tif -o out.tif --stock superia800
```

These absorb the scanner's per-unit spectral response and the film stock's dye
characteristics. The generic pipeline (no `--stock`) also works well for any
C-41 film.

### Lab mode

A real LS-600 operator told us they dial contrast -2, highlights -2, shadows -2,
sharpness 3-5, and auto contrast 5 on every scan because the defaults are too
contrasty. `--lab` applies those same corrections:

```
python -m noritsu.cli scan.tif -o out.tif --lab
```

Equivalent to: `--contrast 0.90 --gamma 0.90 --toe 0.04 --sat 0.95 --real-curve`.
A gentler, more print-ready rendering.

### ICE was not the culprit

We previously thought the remaining gap was ICE/dust masking, but the owner
sent frames with ICE disabled and the NCC was the same. The residual is
consistent regardless of ICE state. The real gap is per-film spectral response
and the missing `SpecialPcb` per-film tables.

## LS-600 raw scan input

`noritsu/ls600raw.py` decodes the scanner's `FULL*.RAW` frames
(headerless 3×uint16 LE BGR, 12-bit data, 6391×4042):

```python
from noritsu.ls600raw import load_ls600_raw
arr = load_ls600_raw("FULL000000010000.RAW")   # float32 (6391,4042,3) BGR [0,1]
```

Feed that straight into the CLI or `pipeline.process_negative`. The loader is
new; sizes/order were recovered from real LS-600 frames and verified against
the machine's own outputs.

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

## Coolscan → Noritsu workflow (2026-08-04)

This pipeline works with any scanner's linear C-41 raw, not just the LS-600.
The density inversion is scanner-agnostic — the math doesn't care which CCD
captured the transmittance.

### From Scan Studio archive

Scan Studio exports full-res linear TIFFs in its `Archive/` folder:

```
python -m noritsu.cli ScanStudio1.tif -o noritsu_render.tif \
  --gamma 0.8 --contrast 1.15 --sat 1.2 --dmax-pct 98.0 --preview
```

### Tuning for your negative

The defaults assume a normally-dense C-41 negative. If your frame looks
underexposed (thin negative), the pipeline compensates:

| Negative | `--dmax-pct` | `--gamma` | Result |
|---|---|---|---|
| Normal/dense | 99.5–99.8 | 0.9–1.0 | Standard Noritsu |
| Thin/underexposed | 98.0 | 0.7–0.8 | Lifted, open shadows |
| Overexposed/dense | 99.9 | 1.0–1.1 | Rich, punchy |

Key insight: gamma > 1 on a low-contrast positive makes things *darker*.
For a thin negative, lower gamma (0.7–0.8) lifts the image to proper exposure.
Add `--contrast 1.05–1.15` to restore snap.

The real LS-600 calibration (`--calib`) does not transfer to other scanners —
it encodes the LS-600's specific CCD spectral response. The generic pipeline
is the correct approach for cross-scanner use.

### Validated

A real LS-600 owner's raw frames plus a Coolscan 5000 full-res archive both
produce beautiful Noritsu-style positives through this pipeline.
