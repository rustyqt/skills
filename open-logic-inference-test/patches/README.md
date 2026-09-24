# Inference Test Windows Patches

This folder holds **Windows-portability patches** for the Open Logic synthesis-inference test
framework (`tools/inference_test/`). The upstream framework targets Linux and uses two patterns
that do not work on a stock Windows Python install:

1. `pexpect.spawn(...)`: only available on Unix (uses pseudo-terminals). On Windows, `pexpect`
   does not even expose `spawn` as a module attribute, so the import fails immediately. The
   patched files use `subprocess.run(...)` instead.
2. `FileSystemLoader("/")` with an absolute path passed to `get_template(...)`: Jinja2 splits
   template names by `/` and rejects Windows paths like `D:\open-logic\...`. The patched files
   root the loader at the script directory and pass a relative template name.
3. Backslash paths leaking into rendered Tcl scripts: Tcl interprets `\t`, `\o`, etc. as escape
   sequences. The patched `ToolLibero.py` normalises paths to forward slashes before rendering.

The patches are kept **out of the git-tracked source tree** so day-to-day development on the
upstream Linux flow is unaffected. They are applied only when running the synthesis inference
test framework on this Windows host.

## Files

| File                  | Replaces / copies to                                        |
| --------------------- | ----------------------------------------------------------- |
| `TopLevel.py`         | `tools/inference_test/TopLevel.py`                          |
| `ToolLibero.py`       | `tools/inference_test/ToolLibero.py`                        |
| `InferenceTest.py`    | `tools/inference_test/InferenceTest.py`                     |
| `top.template`        | `tools/inference_test/top.template`                         |
| `synthesize.template` | `tools/inference_test/tools/libero/synthesize.template`     |
| `fmax.yml`            | `tools/inference_test/yaml/fmax.yml` (sample, remove after) |

## Fmax timing measurement (optional, `OLO_TIMING_REGS=1`)

Beyond the Windows-portability fixes, the patches add an optional maximum-frequency flow, **gated by
the `OLO_TIMING_REGS` env var** (inert when unset, so the same patch set serves plain resource runs):

- `top.template` — adds `use olo.olo_ft_pkg_ecc.all` (resolves `eccCodewordWidth` in the test
  wrapper) and, when gated on, a Clk-domain register ring around the DUT so boundary logic (ECC
  encode/decode, scrubber address mux) is timed reg-to-reg instead of being false-pathed.
- `synthesize.template` — when gated on, writes an SDC clock constraint and runs `PLACEROUTE` +
  `VERIFYTIMING` with a SmartTime script that dumps `max_timing.rpt`.
- `ToolLibero.py` — `get_fmax()` parses the achieved `Clk`-domain frequency; renders the template
  with `fmax` from the env var.
- `TopLevel.py` — passes `timing_regs` (from the env var) into the wrapper template.
- `InferenceTest.py` — prints `Fmax(Clk)` per config and archives `results/<entity>__<config>__max_timing.rpt`.

See the skill `SKILL.md` ("Fmax / timing measurement") for the full apply/run/revert + readout.
