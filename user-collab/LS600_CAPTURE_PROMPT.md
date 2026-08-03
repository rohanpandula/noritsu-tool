# LS-600 Captures — what to collect (hand this to the operator's Codex)

You are helping capture reference data from a working Noritsu LS-600 film
scanner system for a color-pipeline reverse-engineering project. The goal is to
collect the raw inputs and ground-truth outputs for ONE film frame (ideally a
couple of film stocks: Portra 160/400, Gold, Ektar), plus diagnostic files that
reveal how the EZ Controller drives the engine.

Run one real scan and capture the following, in priority order. Put everything
in a single folder, e.g. `C:\noritsu_capture\FRAME_01\` and zip it when done.

## 1. The raw negative frame (most important)
The scanner keeps linear 16-bit scan data on disk that is normally not shown to
the user. Find it: it may be a large raw file (tens of MB), headerless or
unknown extension, written during/after a scan. Look under the EZ Controller /
ImageDataProc data dirs and any temp/working directories. Common candidates:
  - `C:\noritsu\ImageDataProc\Data\...`
  - `C:\noritsu\ImageDataProc\$LogData$\$Film Scan$\...`
  - any `*.dat`, `*.raw`, `*.imx`, `*.buf`, or large unlabeled files created at
    scan time (sort by timestamp/size on the scan).
If unsure, snapshot the directory listing BEFORE and AFTER a scan and identify
files that appeared. Record each candidate's extension and byte size. Do NOT
open/convert the raw files — we recover the format from the header ourselves.

## 2. A corrections-off linear negative export
From EZ Controller (or a companion tool), export the NEGATIVE as a 16-bit TIFF
with ALL corrections off: no auto white-balance, no color correction, no
gamma/tone curve, as-shot/linear. If the export dialog has "raw/linear" or
"no adjustment" options, use them. This is the "input side" of the pipeline.
(If only the finished positive can be exported, export that too but label it
OUTPUT, not INPUT.)

## 3. The machine's finished output (reference)
The normal finished positive/inverted TIFF the machine produces for that same
frame, exported from EZ Controller, ideally the same scan session. This is the
"reference output" we calibrate against.

## 4. The engine's command + log transcripts from that scan
Grab every file written during the scan:
  - `C:\noritsu\ImageDataProc\$LogData$\$Film Scan$\XC_CorrIn_*.xml`
    (the actual command documents the host sent to the engine)
  - `NKCImgLog_*.txt` and `Accu*.txt` logs in the same folder
Record the exact scan timestamp so the files can be matched to FRAME_01.

## 5. The correction file + parameter tables in use (if exposed)
  - any `*.cf` correction file the run used (often in a `Data\...\CorrectServ\`
    tree, and the `PCB_PARA\*.dat` tables in
    `C:\noritsu\ImageDataProc\Data\CorrectServ\IQGrp000\00000000\PCB_PARA\`)
Just copy the PCB_PARA folder as-is if present; do not alter it.

## What to return
- The zipped folder with per-frame subfolders (neg raw, input tiff, output
  tiff, xml/logs), each frame labeled with film stock + exposure + scan
  settings used.
- A short text file (MANIFEST.txt) listing: scanner software/version, OS,
  per-file purpose (input/output/raw/log), extensions + sizes of any raw
  candidates, and whether corrections were fully off.
Do not post-process, color-correct, or re-encode any of the captured files.
