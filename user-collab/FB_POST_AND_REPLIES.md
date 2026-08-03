# Facebook post drafts — Noritsu group LS-600 help request

Final message to the group (LS-600 only):

Have an LS-600? I need exactly one negative→positive pair from it.

I've been reconstructing the LS-600 / EZ Controller 6.5 color pipeline from the
software itself — pulled the real per-film correction tables (gamma/contrast/
white-balance from SpecialPcb.dll), the CommonCalcPara tone curve, mapped the
RD5X processing chain, and rebuilt the engine's correction-file format from the
binaries so it runs headless. What I don't have is a reference output from the
actual machine to confirm the rendered look on real film.

The one thing that unlocks the whole project — a single pair, LS-600 only:
1. The raw negative scan from the LS-600 (16-bit TIFF, corrections off / as-shot,
   film border visible is a bonus).
2. The LS-600's own inverted output of that same frame (whatever the machine
   normally produces).

Same frame, both sides. Film stock + scan settings noted. That's it — one pair
is enough to calibrate the entire pipeline end-to-end and pin down, for the
first time computably, what the "LS-600 look" actually is (vs. what presets
*guess* it is).

I want us to be able to prove it, not approximate it. If you've got an LS-600
and a minute to run one frame through it, reply or message me — I'll send a
folder link, you drag two files in, done.

## Reply to questions
- "Is it tuned to hardware or would it work on a Coolscan?" — the 2-sided answer:
  color science/inversion is scanner-agnostic density math (already solved);
  the LS-600's CCD gain/shading/linearization is the hardware side. Coolscan
  works after a one-time per-channel calibration.
- "Raw internal file vs 16-bit TIFF export from EZ Controller?" — want the
  NEGATIVE, un-corrected, linear 16-bit. Best: the raw 16-bit frame file on
  disk (we decode the internal raster format ourselves). Also fine: 16-bit TIFF
  export of the negative with corrections OFF (not the finished positive).
