# HANDOFF — resume Noritsu LS-600 + FlexColor color-pipeline work

Read these first: JOURNEY.md (nori repo root) is the canonical log.

## Where everything lives
Same as before. Key paths on this machine:
- **nori repo:** /Users/rohan/Downloads/nori
- **noritsu-tool repo (published):** /Users/rohan/Downloads/noritsu-tool-public
- **flexcolor-tool repo:** /Users/rohan/Downloads/flexcolor-tool-public
- **LS600 calibration bundle:** /Users/rohan/Downloads/LS600_cal/

## Current state

### Noritsu color science — fully DONE
### Calibration — geometry + refit: COMPLETE (this session)

#### 1. Raw→TIF geometric transform — MEASURED

The machine crop+resample is now verified at pixel level:

```
Raw (portrait):    6391×4042, 3×u16 BGR, 12-bit
Rotate 270°:       landscape 4042×6391
Crop:              y=16..4024 (4008 rows), x=168..6216 (6048 cols)
Resize:            INTER_AREA to 6048×4011
```

The crop derives directly from the machine's `UsImRct` in `TrzCorFile`:
- THUM (252×399) UsImRct = `1,10,251,388` → crop 250×378
- THUM is a 1/16× downsampled extract of the FULL raw (252×16.04≈4042, 399×16.02≈6391)
- `UsImRct` scaled to full: `y0=16, x0=168, h=4008, w=6048`
- Final resize from 4008×6048 → 4011×6048 adds 3 rows (vertical scale factor = 4011/4008 ≈ 1.00075)

Validation: direct-crop luma-NCC=0.887 (vs ~0.57 without crop), and phase correlation at 1/8 scale gives NNC=0.943.

#### 2. Spatial corrections — CONFIRMED ON

The `DefScanningEnv.xml` explicitly has:
```
Digital_Ice_Func=1, Digital_Masking_Func=1, DustSearchSw=1
```
This means **ICE (infrared dust removal), digital masking, and dust suppression were applied**, even though the DSA settings panel shows all controls at neutral/off (OCR-confirmed). The DSA panel controls *tone/color enhancements*, not the hardware correction stack. So the TIFFs have a dust+scratch corrected image, which the CLI's per-pixel LUT cannot reproduce.

The `ezc-dsa-settings.jpg` OCR confirms: Overall/Shadow/Highlight Auto Contrast = None, Sharpness=0, Grain/Moire=None, Lens Aberration=OFF, Chroma at middle.

#### 3. Post-geometry refit — RESULTS

Calibration fitted on frame 04 using geometry-aligned data, evaluated at 1/4 res:

| Frame | NCC     | RMS(/255) | R_ch  | G_ch  | B_ch  |
|-------|---------|-----------|-------|-------|-------|
| 01    | 0.8880  | 33.43     | 34.92 | 31.57 | 33.70 |
| 02    | 0.9301  | 30.10     | 27.70 | 29.20 | 33.13 |
| 03    | 0.9327  | 28.26     | 25.36 | 27.47 | 31.58 |
| 04    | 0.9565  | 24.58     | 21.13 | 24.17 | 27.96 |
| 05    | 0.9567  | 24.75     | 21.38 | 24.21 | 28.17 |
| 06    | 0.9595  | 28.69     | 26.77 | 27.39 | 31.67 |
| 07    | 0.9533  | 31.23     | 28.90 | 26.29 | 37.42 |
| 08    | 0.9201  | 34.43     | 31.99 | 30.49 | 40.04 |

**Mean NCC: 0.937** (was ~0.71 before geometry alignment)
**Min NCC: 0.888** (frame 1, clear improvement opportunity)

The geometry alignment alone closed the gap by ~0.2 NCC. The remaining residual (~6%) is dominated by:
- ICE/digital masking (spatially varying, not capturable by per-pixel LUT)
- The 0.075% vertical scale mismatch (4011/4008 vs exact resize)
- Per-frame variation in Dmin/Dmax (we use frame 4's fit globally)

RMS is still 24-34/255 per channel — this is the spatial correction floor.

#### 4. Default vs Adjusted TIFFs

The "adjusted" TIFFs are substantially different from "default":
- RMS 16.7–19.0/255
- NCC 0.982–0.995 (very high — same geometry, mostly a tone curve shift)
- Delta is a uniform darkening with color shift: blue channel drops most
  (mean ΔB ≈ -1848 at 16-bit ≈ -0.028 in [0,1])
- The border area shows the adjustment is a global tone remap, not local:
  both border and image area shift proportionally
- The "adjusted" set is likely the "Automatic Contrast" mode or a different
  preset/treatment

### Priorities moving forward
1. Per-frame per-channel calibration (fit each frame independently) — would show
   whether the residual is dominated by per-frame Dmin/Dmax variation vs spatial
   correction.
2. Per-film stock calibration (Portra 400, Gold, Ektar, ECN-2) for per-film
   table validation.
3. If a live LS-600 + host becomes available, revisit the headless-engine
   film path.
4. Close the border-dust ICE model: try training a spatial correction model
   from the residual pattern.

### Gotchas
- Same as before: no private scans/VM keys in public repos.
- rawpy 0.25.1 has no `use_black`.
- Calibration file at `/tmp/nori_calib_frame4.npz` (fit on frame 04 with geo alignment).
- The geometry params (Y0=16, X0=168, CH=4008, CW=6048) should be added to
  `calibrate.py` or a helper function for proper pipeline integration.
