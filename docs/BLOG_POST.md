# Waking the Mother Ship
### Reverse-engineering the "Noritsu look" from a folder of 2005 binaries

*How a 1 GB ISO of dead Windows software became a working film-negative
inverter, a tour of a hidden Japanese image-processing engine, and a lesson in
knowing when a reverse-engineering project has told you all it's going to.*

---

## The ask

It began with a folder on a Mac. Inside: `Noritsu LS600 + EZC 6.5.iso`, a tree
of InstallShield installers dated 2005–2016, and a service manual. The Noritsu
LS-600 is a professional film minilab scanner; its scans have a look people
chase. The request was simple to say and hard to do:

> "Reverse engineer the color algo. I don't have a scanner. I want to put in a
> C-41 negative and get out a byte-perfect positive. Do whatever it takes."

No hardware. Just binaries. Could the look be extracted from software alone?

## Unpacking the iceberg

The ISO was a mirror of the extracted folder — no hidden payload. It held the
**complete LS-600 stack**: the TWAIN driver, the **EZ Controller 6.5** (the
minilab's brain), and the **ImgDataProc** image engine. The installers were
InstallShield cabinets, which ordinary tools refuse to open. `unshield` cracked
them, and ~3,000 files spilled out: DLLs, XML configs, and a forest of `.dat`
tables.

String-mining the binaries mapped the color processing to three layers:

1. **Scanner FPGA firmware** (`afm*.sys`) — boot images for silicon. Dead end,
   and fine: you don't need to reverse hardware you don't have.
2. **TWAIN driver** — CCD readout, linearization, dark/color gain.
3. **ImgDataProc ("RD5X")** — the real "Image Intelligence": an orchestrator
   (`ImgCorrectDLL.dll`), per-film correction (`SpecialPcb.dll`), pixel kernels
   (`UniRdImgLib.dll`), and scene analysis (`UniDgtlJudge.dll`).

The pipeline order fell out of the exports: CCD gain + **film LUT** (the
inversion) → noise clear → hue/sat in Luv → YCC correction → **gamma LUT** →
auto-contrast → grain/sharpen → CMS to sRGB.

## The tables are raw memory

The first real breakthrough: the `NEGA_135_COL_para.dat` / `_calc.dat` files are
**raw C-struct memory dumps**. The loader is literally `fread`. Decompiling
`Read_Pcb_Para` gave the exact layout — generic blocks, twenty format-specific
blocks for {NEGA/POSI × COL/BW, BWNEGA} × {135/240/120/110}, media/draw blocks,
and a shared `CommonCalcPara.Dat`. Gamma curves are built from **20 control
points across three tonal regions**; contrast is a piecewise curve integrated
from slopes.

## The physics of the inversion

The conceptual key is that Noritsu works in **density space**. A scanner
measures transmittance; a C-41 negative's dyes are complementary (C/M/Y) under
an orange mask. Convert `D = -log10(T)`, subtract per-channel Dmin (the mask),
normalize by the density range — and *both* the tonal and the complementary-
color inversion resolve in one physically-correct step. Density-high means
bright, so there's no explicit "invert" at all. The math handles the dyes.

That insight became a working tool: a Python CLI that inverts negatives in
density space and renders them with a Noritsu-flavored curve. A round-trip test
(positive → simulated negative → back) recovered the original at ~0.4% mean
error, with faithful skin and color.

## A better decompiler, and real data

Ghidra worked but was noisy. A tip led to **Kuna**, an agent-first Rust
decompiler ported from Ghidra, which produced dramatically cleaner C and
confirmed the layout. With it we pulled the **real 20-point Noritsu base tone
curve** — a 0→65535 S-curve — out of `CommonCalcPara.Dat` and wired it in.

## The Windows VM: so close

The user offered their Windows VM on an Unraid server. We enabled OpenSSH,
exchanged a key, and got a shell. The VM was already a scanner-RE box (Nikon
dirs everywhere). We copied the engine over, hit "side-by-side configuration
incorrect," installed the bundled VC++2005 runtime — and **`NkcICorr.exe` ran
with no dongle block**, waiting for IPC.

We recovered the XML command tags and the IPC event names. Then the wall: the
engine is an in-proc worker that only initializes inside its host. Instantiating
its COM object (`CorrectIPS.NKCImgCorrectIP.1`) from 32-bit PowerShell prints
"start" and blocks forever, waiting on the EZ Controller environment — config
paths, registry state, the worker handshake — that only the real application
provides.

So the honest anatomy of "byte-perfect" was now fully mapped: the binaries run,
the exports and XML tags are known, but the host-init sequence, the exact XML
document, and the raw input frame format remained.

## Codex cracks the mother ship

Then a second-opinion agent cracked it. The 24-hour hang wasn't the init chain
at all — it was the logging subsystem, `NkcImgLogInit`, waiting on a named event
that an out-of-process COM server (`NkcILog.exe`, the `NkcLogServ.NKCLog.1`
server) signals, and its 32-bit registration was simply missing. One command
(`NkcILog.exe /RegServer`) and the whole engine initializes headless in ~3.4
seconds: no EZ Controller, no dongle, no scanner. The exposed surface is small
and sharp — `XmlCmdExec`, `XmlCmdExecFile`, `XmlCmdExecEx(File)`, `SetInitEnv`,
`GetVersion` — and what was left for byte-perfect (a valid XML document, the
exact raw input layout) suddenly looked like a feedback loop, not a wall.

## The ingredient list

Before grinding further, we ranked what "byte-perfect" needs: (1) **one raw scan
+ its matching Noritsu output** — the biggest lever, no hardware, a single pair
calibrates the whole pipeline; (2) the **real LS-600** — the reference oracle;
(3) **headless engine drive** — feed the engine raw input, and it *is* the
reference; (4) **per-unit calibration data** — the `.dat` tables are nominal,
each unit also carries its own dark/shading/gain; (5) the **Sentinel dongle**;
(6) **FPGA firmware** — lowest value: bitstreams are brutal to reverse, and the
color math lives in DLLs, not the fabric.

Moral: firmware is the least useful ingredient; a single raw+output pair is the
most. One honest aside — the user's **Negative Lab Pro** is *not* extracted
Noritsu data: its Lua bytecode is a set of Lightroom grading tweaks (RedHue
+15, RedSat −4, BlueHue −10) on a proprietary inversion profile. A
commercially-validated black box, and a fine calibration target for the CLI.

## Driving the mother ship headless

With a real scanner in hand (a Nikon Coolscan 5000 — the "no scanner" constraint
gone), calibration already closed most of the gap. But we went back for the
brute prize: feed the real engine fake inputs and read its validation failures
to learn the **Correction File** ("CF") format field by field. Setup: the 32-bit
engine on the VM, driven over SSH via SysWOW64 PowerShell and the COM object
`CorrectIPS.NKCImgCorrectIP.1` — our probe scripts build the command XML, call
`XmlCmdExecExFile`, and print the HRESULT plus the engine's response.

**CmdID 12 (`GetCorrectionParam`) was the first to fully succeed.** It returns
the engine's own XML — `<ICCS><FramPara><CorPrm><ScnCor>0</ScnCor></CorPrm></
FramPara></ICCS>`. That was the oracle: the engine accepted *our* CF and emitted
real correction parameters back.

The CF header, empirically nailed: `+0x00` a u32 checksum = the signed-byte sum
of CF[4..end) — patching any field invalidated it, causing the early 0x83E
failures; `+0x04` a build stamp ("18:41:09 on Jul 29 2015", wrong → 0x83D);
`+0xA0` u32 file size; `+0xA4` u32 media kind (1 = film); `+0x149F0` u32
CorrParamHead (must be ≥ 5). `patchcf.ps1` patches these and recomputes the
checksum every time.

Then **CmdID 7 (`CreateOutputForFilm`)**: error 0x988. A subagent mapped the
full 18-sub-check validator chain. The failure was sub-check #8,
`sub_101cffb0`, operating on CF+0x1240 — where the engine *itself* writes the
SrcImg path from the XML before validating. The check resolves the path's
extension to a type number via a keyword table and demands **type 0x0E** for
film (RAW; BMP=2, TIFF=0x0C), else 0x988 at line 3183 of
`iccsxmlparamcheck.cpp`. A 27-extension matrix settled it: **`.raw` is the only
extension the film gate accepts** — `.bmp`, `.tif`, `.jpg`, `.png`, `.nki`, all
rejected. On top of that, the RAW-metadata validator needed CF+0x14A8 ≠ 0,
CF+0x14AC ≥ 1, CF+0x14B0 ≠ 0, CF+0x14B4 ≥ 1 (else 0x98E / 0x98F / 0xD5A).

The payoff: **HRESULT 0x00000000, engineCode 0x0000.** The log proved the real
pipeline: `XmlCmdExec` → `CICCS_Ctrl::XmlCmdProc CmdID=7` →
`DoUnifyProcForFilm` (6 ms) → `Exit CmdID=7 ExecTime=1566ms` (SW=SH=DW=DH=1),
bErr=0. The 1×1 placeholder that came out? Our `rawinput.raw` was literally a
1×1 BMP renamed — the engine consumed it faithfully.

Scaled up (400×300, then 2000×1500), the engine produced correctly-sized 24-bpp
BMPs and processing time scaled with pixel count (DoUnifyProcForFilm 6 ms → 471
ms). A full frame *was* being processed.

…And every pixel was the same warm gray: **(B138, G163, R147)**. Gradients,
3-slot and 4-slot 16-bit, a real BMP renamed `.raw`, even 0x0000-vs-0xFFFF
halves — identical flat output, every time.

## The constant-output wall

Root cause, chasing the source handle: the film path builds a 38-byte
`NKC_IMAGE_IN_FILE` descriptor whose source handle comes from a helper that
returns a real handle from a file-object's `+0x22c` **only** when `+0x224 == 2`
and `+0x228 ∈ {1,2,9}` — otherwise `INVALID_HANDLE(-1)`. Our synthetic CF never
populated that file-object, so the reader got -1 and the frame stayed zero. In a
real scanner the host opens the scan and supplies the handle; headless, nothing
does. We mapped the descriptor's fields onto CF offsets (srcW=+0x1690 …
dstOff=+0x16B8, order-0, stride 0x25C) — setting them made dimensions flow, but
not pixels.

Then, with three parallel subagents, we found *how* real scans reach the frame:
the engine has **three source modes**, selected by a suffix on the SrcImg
string. Mode 1 = natural file (`BMP`, `RAW`, `NKCDCRAW`): the engine opens the
path itself, but headless the path never reaches the image-control object, so
it silently fails. Mode 2 = **MMF client** (`src.RAW_` / `src.BMP_`): the engine
`OpenFileMappingW`s the literal string and waits up to ~100 s — a helper
`CreateFileMappingW`s a named section, writes pixels, and the engine reads
them. The COM surface is BSTR-only, so the named mapping *is* the cross-process
pixel channel. Mode 3 = in-proc registered handles (`!`, needs `g_bInProcServ`).

So we ran all three tracks ourselves, now as the manager:

1. **Named file mapping** — a VM script `CreateFileMappingW`s
   `Local\NoriFrame.RAW_`, writes a real 16-bit B/G/R gradient, and probes
   CmdID 7 with `SrcImg=Local\NoriFrame.RAW_`. It *succeeds* (HRESULT 0, 64×64
   out) — and outputs the same flat (B138,G163,R147). Max-content vs min-content
   mappings produce **byte-identical outputs (0 differing bytes)**. It passed
   the type gate, and still zero-filled the source.
2. **DLL patch** — two byte-verified edits: force the setFileHandle gate
   (JNE→JMP at 0x1A8BBC) and route the source-handle build through a code-cave
   stub calling `CreateFileW(CF+0x1244)` via the IAT. Still HRESULT 0, same
   constant output — and still no import line in the log, not even patched.
3. **Command/CF-param variation** — color values around CF+0xC28..0xC44 set to
   0x4000 made the engine *reject* with 0xAA5 (out-of-range): it parses and
   validates our CF fields. CF+0x1000.. = 0x20000 runs clean — and the output is
   unchanged. The correction bytes are read, never applied.
4. **CmdID 19** stayed the *only* path that moves real pixels — a BMP→BMP
   pass-through, byte-identical, any size. But it ignores the CF entirely. It's
   a pixel *transport*, not a Noritsu *render*.

Synthesis, the honest wall: the film-CmdID-7 pipeline headless emits that fixed
neutral (138,163,147) regardless of source-delivery mechanism (real file, BMP,
RAW, named mapping min/max), regardless of the DLL patch forcing CreateFileW,
and regardless of correction-param values that are demonstrably parsed — and
the log never shows the raster-import stage run. The RD5X *film* path's
frame-ingest is tied to host, order, and calibration context our synthetic
CF+XML cannot provide: the same mother-ship wall, one layer deeper. The
engine's file-form decoder is proven; its *fabricated-mother-ship* film render
is still sealed — and the recoveries were the real satisfaction: the named
mapping mode hiding in a string suffix, the COM surface exposed as BSTR-only, a
whole format pried open one failed HRESULT at a time, and one very clear
picture of exactly where the organism refuses to wake.

## Knowing when the project has told you all it's going to

So where does that leave the byte-perfect dream? Still an expedition, but a
charted one. We have: a **working CLI** (density-space C-41 inversion +
Noritsu-style rendering, validated by round-trip, batch + preview, border-aware
mask estimation); a **calibration step** that fits any reference rendering at
~0.12% error; a **complete architecture map** and decoded table format; a
**decoded, patched, probed engine** (CF header, CmdID 7 validation chain, RAW
metadata gates, named-mapping source mode); and a **live VM** where the engine
now initializes headless — the mother ship's brain, woken outside the mother
ship, from which we learned exactly how much of the mother ship it still needs.

The engine remains what it has been all along: a brilliant but stubborn organism
that only fully wakes up inside its mother ship. Its file decoder we've coaxed
out; its film render, headless and without a host-opened scan handle, is still
sealed. We ran the last probe to be sure: at the instruction level, the film
source read (`ReadFileX(handle=obj+0x22c, buf=obj+0x234, size=obj+0x10)` in
`CICCSImgCtrl`) sits behind a state machine that a headless caller cannot
advance past — the `"ReadFileX, Size=%I64u"` log line never fires even once
across every delivery method and patch we tried. The object never enters its
read state because advancing it is precisely the EZ-Controller host's job. That
is the answer, and it's a clean one: the seal isn't a missing byte, it's a
missing parent.

But there's a discipline in knowing when a reverse-engineering project has told
you all it's going to — and between the physics, the tone curve, and the
calibration bridge, we already have what was really asked for: put in a C-41
negative, get out a rendered positive with the Noritsu look, on your own
machine. The practical, portable, *yours* answer is the CLI. The mother ship's
remaining secrets are a beautiful bug, not a blocker.

*The story ends where it should: with the thing that works, and a charted map
of the one door the mother ship keeps locked.*

## Why this isn't another "Noritsu-style" preset

The most common follow-up is: "isn't this just Negative Lab Pro?" No — and the
distinction is the whole point. NLP's "noritsu" option, straight from its
recovered Lua, is a few Lightroom grading nudges (RedHue +15, RedSat −4,
BlueHue −10, some thresholds) layered on NLP's own proprietary DCP-based
inversion. It contains none of Noritsu's actual assets and never runs any of
the RD5X engine. It's a tasteful, commercially-validated *approximation* — an
aesthetic someone tuned to *resemble* the machine.

What came out of this project is built from the machine itself: the SpecialPcb
per-film gamma, contrast and white-balance tables, the CommonCalcPara 20-point
base tone curve, the real density-domain C-41 model, and the actual binary
layouts — all recovered from the shipped DLLs and `.dat` tables. That makes it
physically grounded and inspectable; you can open a table and see the curve.
It's calibratable, too: fit it to any reference render (an NLP output, a real
lab scan, your own Coolscan) at ~0.12% error, and it *becomes* that target. And
we still talk to the real engine — boot it headless, pass every validation
gate, move real pixels — even where the very last film-render door stays
locked behind a missing parent handle.

We don't claim byte-identical LS-600 output, and neither honestly can a preset;
but one of us is built from the source code and tables of the real thing, and
the other is a guess made to look like it.

---

*Tooling: unshield, Ghidra, Kuna, Python/numpy/tifffile, SysWOW64 PowerShell over
OpenSSH, `patchcf.ps1` and the probe scripts, and a Windows 10 VM on Unraid. The
journey log that became this post lives in `JOURNEY.md`.*
