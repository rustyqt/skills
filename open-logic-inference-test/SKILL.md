---
name: open-logic-inference-test
description: >-
  Run the Open Logic synthesis inference test on this Windows host. The upstream framework
  (tools/inference_test/) targets Linux; this skill covers the Windows-portability patches bundled
  with this skill (pexpect to subprocess, Jinja2 template loader, backslash path normalization) and
  the apply to run to revert workflow with Libero. Use whenever
  the user wants to run, set up, or debug the synthesis/inference test on Windows, check resource
  inference (BRAM / register / TMR mapping) for an olo_* entity, run InferenceTest.py, drive Libero
  (Microchip Designer) synthesis on this host, or asks why the inference test fails on Windows.
  Covers Libero PATH setup, per-entity and per-config runs, reverting the patched files to keep the
  working tree clean, and the status of the other synthesizers (Vivado / Quartus / Gowin / Efinity /
  Cologne Chip). Reach for this skill even when the user just says "run the inference test" or
  "synthesize this entity" on this machine.
---

# Open Logic Synthesis Inference Test (Windows / Libero)

The Open Logic synthesis inference test (`tools/inference_test/`) confirms that entities map to the
intended hardware resources (block RAM, registers, TMR preservation) under a real synthesis tool.
The framework targets the Linux CI runner and is not portable to Windows as-is, so on this host it
is run with local patches plus Libero.

This skill is the workflow authority. The patched files are bundled in this skill's `patches/`
directory — kept here, outside any git repo, so the upstream sources stay clean: `TopLevel.py`,
`ToolLibero.py`, `InferenceTest.py`, `top.template`, `synthesize.template` (plus a sample
`fmax.yml`). `patches/README.md` explains what each patch changes and why. The patches carry two
things: the Windows-portability fixes (always active) and an **optional Fmax timing measurement**
flow gated by the `OLO_TIMING_REGS` env var (see "Fmax / timing measurement" below). The Fmax
additions are inert when the env var is unset, so the same patch set serves both resource and timing
runs.

For *developing* an entity use the `open-logic-dev` skill; for getting ft entities *upstream* use the
`open-logic-ft-pr` skill. This skill is only about running the inference test on this machine.

## Why the patches are needed

The upstream framework uses three patterns that fail on a stock Windows Python install. The patched
`TopLevel.py` and `ToolLibero.py` fix exactly these and nothing else:

1. **`pexpect.spawn(...)`** is Unix-only (pseudo-terminals); on Windows the import fails outright.
   The patch uses `subprocess.run(...)` instead.
2. **`FileSystemLoader("/")` with an absolute template path** — Jinja2 splits template names on `/`
   and rejects Windows paths like `D:\...`. The patch roots the loader at the script/tool directory
   and passes a relative template name.
3. **Backslash paths leaking into rendered Tcl** — Tcl treats `\t`, `\o`, etc. as escapes. The patch
   normalizes paths to forward slashes before rendering the Libero Tcl script.

## Setup

Libero ships with the Microchip install but is not on PATH. Prepend its `Designer\bin` in the shell
session that will run the test:

```powershell
$env:PATH = "D:\Microchip\Libero_SoC_2025.2\Libero_SoC\Designer\bin;$env:PATH"
```

## Apply, run, revert

Run from the root of the repository under test (the `open-logic` repo). The patches **overwrite the
two tracked files**, so they must be reverted after the session.

```powershell
# 1. Apply the patches (bundled in this skill)
$p = "$env:USERPROFILE\.claude\skills\open-logic-inference-test\patches"
Copy-Item "$p\TopLevel.py"         tools\inference_test\                 -Force
Copy-Item "$p\ToolLibero.py"       tools\inference_test\                 -Force
Copy-Item "$p\InferenceTest.py"    tools\inference_test\                 -Force
Copy-Item "$p\top.template"        tools\inference_test\                 -Force
Copy-Item "$p\synthesize.template" tools\inference_test\tools\libero\    -Force

# 2. Run the inference test (see "Running specific entities" below)
cd tools\inference_test
python InferenceTest.py --yml=yaml/base.yml --tool=libero

# 3. Revert the patched files so the working tree stays clean
cd ..\..
git checkout tools\inference_test\TopLevel.py tools\inference_test\ToolLibero.py `
             tools\inference_test\InferenceTest.py tools\inference_test\top.template `
             tools\inference_test\tools\libero\synthesize.template
```

**Critical:** never commit while the patches are applied — those files would carry the Windows-only
(and Fmax-measurement) changes into the repo (and potentially upstream). Always `git checkout` them
first. Treat the revert as part of the run, not an optional cleanup step.

## Running specific entities and configs

```powershell
# Whole base sweep / whole ft sweep
python InferenceTest.py --yml=yaml/base.yml --tool=libero
python InferenceTest.py --yml=yaml/ft.yml   --tool=libero

# A single entity
python InferenceTest.py --yml=yaml/base.yml --entity=olo_base_ram_sdp --tool=libero
python InferenceTest.py --yml=yaml/ft.yml   --entity=olo_ft_ram_sdp   --tool=libero

# A single entity + named configuration
python InferenceTest.py --yml=yaml/base.yml --entity=olo_base_cam --config=d128-w16 --tool=libero
```

The `--yml` selects the entity set; ft entities live in `yaml/ft.yml` (one representative config per
entity, kept lean for CI). A representative Libero run is ~30–50 s per configuration; the full base
sweep takes a few minutes.

## Fmax / timing measurement

The patches add an **optional maximum-frequency measurement** on top of the resource flow, enabled by
setting `OLO_TIMING_REGS=1`. When set:

- `top.template` wraps the DUT in a **Clk-domain register ring** (registers every DUT data/control
  port; ports whose name ends in `Clk`/`Rst` are excluded) so the boundary combinational logic — ECC
  encode-on-write, decode-on-read, and the scrubber address mux — is timed as reg-to-reg paths.
  Without it that logic sits on false-pathed cross-clock boundaries and Fmax comes out far too
  optimistic (e.g. an ECC RAM reads ~280 MHz instead of its real ~170 MHz).
- `synthesize.template` writes an SDC (`create_clock` on `Clk` + `Framework_Clk`, placed in
  **asynchronous** groups so the reported `Clk` frequency reflects the DUT's intra-Clk paths, not the
  `in_reduce`/`out_reduce` harness on `Framework_Clk`), then runs `PLACEROUTE` and `VERIFYTIMING` with
  a SmartTime script that dumps `max_timing.rpt`.
- `ToolLibero.get_fmax()` parses the achieved `Clk`-domain frequency; `InferenceTest.py` prints it per
  config and archives each config's report to `results/<entity>__<config>__max_timing.rpt` (whose
  "Path 1" shows the critical path).
- The wrapper also `use`s `olo.olo_ft_pkg_ecc.all`, so ports typed with `eccCodewordWidth(...)` (e.g.
  `ErrInj_BitFlip`) resolve in the test wrapper. (This same import is the minimal fix for the latent
  ft synthesis-CI gap: ft RAM configs without `in_reduce` otherwise fail with "eccCodewordWidth not
  declared".)

Wide ports (`Wr_Data`, `Rd_Data`, `ErrInj_BitFlip`, ...) must be reduced via `in_reduce`/`out_reduce`
in the YAML, otherwise the design exceeds the device I/O count. `patches/fmax.yml` is a ready sample
(base/ft RAM sdp comparison + an EccPipeline sweep). After applying the patches (above):

```powershell
$env:OLO_TIMING_REGS = "1"
Copy-Item "$p\fmax.yml" tools\inference_test\yaml\ -Force
cd tools\inference_test
python InferenceTest.py --yml=yaml/fmax.yml --tool=libero      # prints Fmax(Clk) per config
```

Each config runs full P&R + timing (~2.5-3 min, vs ~40 s for synthesis-only resource runs). Read the
numbers from stdout, from `results/fmax.txt`, or from the archived per-config `*_max_timing.rpt`.
Afterwards remove the sample (`Remove-Item tools\inference_test\yaml\fmax.yml`) and `git checkout` the
patched files. Only Libero has a license on this host, so run timing **one process at a time** (do not
parallelize Libero runs); kill any orphaned run with
`Get-Process | Where-Object { $_.ProcessName -match 'libero|synpl|acttcl' } | Stop-Process -Force`.

## Other synthesizers

The same framework also supports Vivado, Quartus, Gowin, Efinity and Cologne Chip via their
`Tool*.py` files. Only **Libero is verified end-to-end on this Windows host.** Vivado 2025.2 is
installed at `D:\AMD\2025.2\Vivado` and is on PATH, but the local install only ships Versal device
support and the local synthesis licence for that family is expired. Running any non-Libero tool on
Windows will likely need the same portability fixes (pexpect → subprocess, Jinja2 loader rooting,
forward-slash paths) applied to its `Tool*.py`; budget for that before promising a run.
