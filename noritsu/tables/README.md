# LS-600 Per-Film Correction Tables

These are the raw color-correction tables from the Noritsu LS-600's
`SpecialPcb.dll` / `ImgDataProc` engine. They define the per-film gamma
curves, contrast LUTs, and white-balance adjustments that give the LS-600
its distinctive look.

## Source

Extracted from the LS-600 EZ Controller 6.5 installer's
`ImgDataProc/Data/CorrectServ/IQGrp000/00000005/PCB_PARA/` directory. These
are the actual files the engine loads at runtime.

## File naming

```
{PREFIX}_{FORMAT}_{TYPE}_{VARIANT}.dat
```

| Part | Meaning |
|---|---|
| `NEGA` | Color negative (C-41) |
| `POSI` | Color positive / slide (E-6) |
| `BWNEGA` | Black & white negative |
| `DRAW` | Drawing / monochrome media |
| `MEDIA` | Print media / photo paper |
| `135` | 35mm film |
| `120` | Medium format |
| `240` | 120/220 medium format (alt) |
| `110` | 110 format |
| `COL` | Color |
| `BW` | Black & white |
| `para` | Parameter table (the source data) |
| `calc` | Calculated / derived table (computed from para) |

## File structure

All files have a **12-byte header** followed by a uint32 LE data array.
The header bytes are:

```
02 01 XX XX 01 00 YY YY YY YY YY YY
```

Where `XX XX` appears to be a version or format ID, and `YY...` is a
repeating pattern that identifies the film type.

### CommonCalcPara.Dat

This is the **master tone curve** — the base S-curve used by the CLI when
`--real-curve` is passed. It's a 20-point control-point curve (0-65535):

```
Input:   0.000 0.001 0.003 0.007 0.013 0.024 0.040 0.063 0.094 0.141
         0.207 0.298 0.418 0.555 0.691 0.811 0.896 0.939 0.971 1.000
Output:  0.000 0.001 0.003 0.007 0.013 0.024 0.040 0.063 0.094 0.141
         0.207 0.298 0.418 0.555 0.691 0.811 0.896 0.939 0.971 1.000
```

Wait — those are the same values? No, the uint32 values are the *output*
levels at evenly-spaced input positions. The curve is:
- Input 0% → output 0
- Input 5% (roughly) → output 76 (0.0012)
- ...
- Input 100% → output 65535

This is a classic S-curve: gentle in the shadows, steeper in the midtones,
rolling off in the highlights.

### Per-film tables (NEGA_*_COL_para.dat, etc.)

These contain per-film adjustments on top of the master curve. The structure
was recovered from `SpecialPcb.dll`'s `Read_Pcb_Para` function:
- 3 generic blocks at the start (0x6006 bytes each)
- 20 format-specific blocks (0x13650 bytes each)
- Each block contains gamma control points, contrast LUT, and WB gains

**The `_calc.dat` files** are the computed/derived versions — the engine
runs `pcb_MakeGammaCurve2` and `MakeContrastLut` on the `_para` parameters
to produce these.

## What film stocks do they cover?

The `NEGA_135_COL_*` files are the generic 135 color negative tables —
applicable to Portra, Gold, Superia, Ultramax, Fuji, and any other C-41
color negative film in 35mm. The LS-600 does **not** appear to have
per-brand or per-DX-code tables. Instead, it has per-film *format* tables
(135 vs 120 vs 110, color vs BW) and the `DRAW`/`MEDIA` tables for
special media.

**Whether the LS-600 dispatches different tables per detected film stock
at runtime is an open question.** The tables exist for multiple formats,
but we haven't confirmed the DX-code dispatch path. The `SpecialPcb.dll`
has a `Read_Pcb_Para` that loads all formats; the runtime selection
mechanism is in the host application (EZ Controller), not the DLL.

## What we know vs what we're guessing

| Claim | Status |
|---|---|
| The tables define per-format gamma/contrast/WB | Confirmed (RE of SpecialPcb.dll) |
| The 20-point curve in CommonCalcPara is the master tone curve | Confirmed (used by the CLI) |
| The engine loads different tables for 135 vs 120 vs 110 | Confirmed (files exist, DLL loads them) |
| The engine uses different tables for Portra vs Gold vs Superia | **Not confirmed** — no evidence of per-brand dispatch |
| The DX code on the film can changes the color pipeline | **Not confirmed** — may only affect the printer/exposure, not the color engine |

## How to use these

The `CommonCalcPara.Dat` curve is already loaded by the CLI via
`--real-curve`. The per-film `_para.dat` tables are not yet decoded into
a usable form — they need the full struct layout from `SpecialPcb.dll`'s
`Read_Pcb_Para` to parse correctly. The `per_film_tables.json` file
contains the raw uint32 dumps for reference.

To contribute: the `_para.dat` files are raw C structs. The struct layout
is documented in `docs/JOURNEY.md` (Chapter 3). A proper decoder would
map the 0x13650-byte format blocks into gamma curves, contrast LUTs, and
WB triples that the pipeline could apply.
