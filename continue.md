# HANDOFF — continue here when the LS-600 captures arrive

Session goal state: **waiting on an LS-600 owner to send reference captures.**
Everything to resume is below. Do not re-derive what's already documented.

## Where things live
- **JOURNEY.md** (nori repo root) — canonical chronological log; read it.
  Latest is **Addendum 15** (the LS-600 collaborator + arrival plan).
- **BLOG_POST.md** — written-up story (incl. the vs-NLP framing).
- **noritsu-tool-public/** — the publishable repo (already on GitHub, public:
  https://github.com/rohanpandula/noritsu-tool). Local clone at
  `/Users/rohan/Downloads/noritsu-tool-public` (branch `main`, pushed).
- **re/CODEX_ADVICE.md** — external Codex consult (operation-list theory + ranked
  bets). Full 20k-line session.
- **re/ImgCorrectDLL_patched_v2.dll** — the extended handle-injection patch
  (tested, ruled out; kept for reference). Original DLL restored on VM.
- **user-collab/** (inside noritsu-tool-public) —
  - `LS600_CAPTURE_PROMPT.md` — paste into the operator's Codex (what to
    collect). THE ask.
  - `FB_POST_AND_REPLIES.md` — the group post + prepared replies.
- `/Users/rohan/Desktop/Exports/LRFrontierExport.tif` — one real NLP/LR
  Frontier export for comparison (not ground truth).

## State of the investigation (concise)
**DONE / working:**
- Noritsu color science: real tables (SpecialPcb per-film gamma/contrast/WB,
  CommonCalcPara 20-pt tone curve), density-space C-41 inversion physics,
  working CLI (noritsu-tool) + `calibrate.py` (~0.12% fit).
- Engine headless on VM (COM `CorrectIPS.NKCImgCorrectIP.1`, boot ~3s), CmdID 19
  real-pixel BMP transport, CmdID 12 oracle, full CF/validation-gate mapping,
  CmdID 7 runs end-to-end HRESULT 0 with correct dims.

**THE WALL (proven, Addenda 9-14):** the film CmdID-7 path never reads pixels
headless. Binary-level proof: `ReadFileX` never fires; the read
(`sub_10182f80`) runs on a host-constructed CICCSImgCtrl object whose state the
EZ-Controller sets at call time; no CF byte / COM param / named MMF / DLL patch
/ handle injection can reach it. `re/CODEX_ADVICE.md` covers the op-list theory
(`sub_101af6a0`, opcode 1 = input) — real but CmdID 7 bypasses the executor.

**LIVE THREAD (the reason to continue):** a real **LS-600 owner** is sending
reference captures. If we get (a) raw linear neg + (b) machine's positive +
(c) `XC_CorrIn_*.xml`/logs, we can:
1. Decode the raw neg with our recovered NKC_IMAGE_IN_FILE raster layout
   (16-bit B/G/R slots; see re/RD5X_INPUT_FORMATS.md).
2. Fit our CLI to the real output via `calibrate.py` → settle "the LS-600 look".
3. Read the real host transcripts to finally understand the
   CICCSImgCtrl setFileHandle/op-list wiring → possibly unlock live-engine
   render.
4. If the operator runs our COM harness against the real host (they offered
   remote desktop later), validate the whole stack live.

## Immediate next steps when captures arrive
1. Put captures in a folder, read manifest, decode the raw neg frame.
2. Run `python -m noritsu.cli <linear_neg> -o <out>.tif` (and punchy params:
   `--contrast 1.45 --toe 0.0 --gamma 0.92 --sat 1.18`), then
   `python -m noritsu.cli [/calibrate.py]` to fit to the LS-600 positive.
3. Compare against `Exports/LRFrontierExport.tif` and the recoveries.
4. Update JOURNEY (Addendum 16+) and BLOG with the calibrated result.

## Side quest (project #2): Fuji Frontier SP-3000 software
- Goal: get the **Frontier SP-3000 operating software / lab-PC install** (the
  prize = its color tables/pipeline, same playbook as Noritsu). Fallback if
  software is unrecoverable: a **neg→positive pair** from an SP-3000 owner.
- Sources to try: Frontier home-lab FB groups; Yahoo Auctions JP (machines/CDs);
  Archive.org + service-forum dark horses. Verify any candidate with me before
  buying (is it the real engine vs a service doc?).
- Known context: the "SP-3000 look" is the contrasty/colorful high-res 35mm
  scan everyone chases — arguably more in-demand than the Noritsu look. It's
  Fuji code, so fresh RE (no table reuse), likely similar effort to Noritsu.

## Environment / gotchas
- VM (Windows, headless engine) still runs; the SSH key path is in the local
  JOURNEY only — never commit it or the VM IP.
- rawpy on this Mac is 0.25.1 — `use_black` kwarg unsupported; io_util now
  subtracts black_level itself (committed + pushed to GH).
- `.arw` support added + pushed (Sony raws now load via rawpy).
- Public repo: MIT, no vendor binaries, no private scans. Do not commit the VM
  key/IP or the private Coolscan TIFFs.
