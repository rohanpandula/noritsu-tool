# LS-600 Per-Film Correction Tables

These are extracted numerical parameters from the Noritsu LS-600's
`SpecialPcb.dll` / `ImgDataProc` engine. They define the per-film gamma
curves, contrast LUTs, and white-balance adjustments that give the LS-600
its distinctive look.

## Source

Extracted from the LS-600 EZ Controller 6.5 installer's
`ImgDataProc/Data/CorrectServ/IQGrp000/00000005/PCB_PARA/` directory.
The original files are vendor binaries not distributed here — this JSON is
our derived knowledge (numbers extracted from the binary structures).

## File naming

```
{PREFIX}_{FORMAT}_{TYPE}_{VARIANT}.dat
```

| Part | Meaning |
|---|---|
| `NEGA` | Color negative (C-41) |
| `POSI` | Color positive / slide (E-6) |
| `BWNEGA` | Black & white negative |
| `135` | 35mm film |
| `120` | Medium format |
| `240` | 120/220 medium format (alt) |
| `110` | 110 format |
| `COL` | Color |
| `BW` | Black & white |
| `para` | Parameter table (the source data) |
| `calc` | Calculated / derived table |

## JSON contents

| File | Role |
| --- | --- |
| `base_tone_curve.json` | **Loaded at runtime.** The CommonCalcPara 20-point base tone curve for each IQ variant (`00000000`–`00000006`). This is what `--real-curve` reads. |
| `per_film_tables.json` | Reference only — extracted numbers and metadata for the full set of per-film table files. No code loads it. |

The raw `.dat` binaries are not shipped; these JSON files carry the
human-readable extracted numbers.

## How to use

The base tone curve loads automatically via `--real-curve`. No vendor data is
needed — the numbers ship in `base_tone_curve.json`:

```
python -m noritsu.cli scan.tif -o out.tif --real-curve
```

If you have a real EZ Controller data tree, point `NORITSU_TABLES` at its
`CorrectServ` directory and the original `.dat` files are read instead:

```
NORITSU_TABLES=/path/to/ImgDataProc/Data/CorrectServ \
  python -m noritsu.cli scan.tif -o out.tif --real-curve
```

The CLI defaults to variant `00000005`. Variant `00000000` is a linear ramp,
i.e. a no-op curve.
