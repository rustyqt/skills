---
name: spacefibrelight-dev
description: Guides RTL and verification work in the CNES SpaceFibre Light IP repository (ECSS-E-ST-50-11C SpaceFibre, VHDL, Versal + NG-Ultra, cocotb/Questa) following the repository's own issue-driven workflow — understand the issue → agree the plan → implement and test in a cocotb scenario → regress both targets and prepare the PR to develop — with user checkpoints before code is written and before anything is pushed. Use when the user asks to create, develop, fix, modify, verify, or contribute RTL, a new module, a bug fix for a GitHub issue, or a cocotb test scenario in the spacefibrelight repository — data link layer, lane / phy+lane layer, MIB, top level, or simulation bench.
---

# SpaceFibre Light — Development Workflow

This skill guides changes to the **SpaceFibre Light IP** ([CNES/spacefibrelight](https://github.com/CNES/spacefibrelight)),
a resource-optimised, partially compliant implementation of **ECSS-E-ST-50-11C SpaceFibre** for AMD Versal (GTY) and
NanoXplore NG-Ultra (HSSL). Most work in this repository is issue-driven modification of existing RTL, so the workflow
is built around fixing an issue. New modules follow the same steps.

**Follow the repository's own practices; do not import process from elsewhere.** In particular:

- **No new requirement schemes.** The only requirement references in this repo are **ECSS-E-ST-50-11C clause numbers**
  (in issues and as `--!Req: <clause>` tags in code) and the **README datasheet sections**. Use those; do not invent
  requirement IDs, requirement tables on disk, or traceability documents.
- **No additional documentation.** Do not create specification, architecture, verification-plan, or verification-report
  files, per-module doc pages, or new diagrams. Update the documentation that already exists (README, `doc/*.md`) only
  where the change makes it wrong or incomplete. Plans and analysis live in the conversation, and in the GitHub issue /
  PR the way the maintainers already use them.
- **PRs look like the existing ones:** a short bullet list of what changed (see PRs #39–#42).

**The repository has no `CONTRIBUTING.md`, no coding-convention document, and no compile/simulation CI.** The rules below
are extracted from the code, `README.md`, `sim/README.md`, the Linty setup, and the issue / PR history. The only CI is
**Linty** (SonarQube-based HDL rule checking plus Yosys/Verific elaboration) on push. **Nothing in CI compiles or
simulates the design**, so the local dual-target regression in step 4 is the only gate. (Precedent: commit `7c877e5a`
"add CDC for no_signal" was pushed with VHDL syntax errors and fixed in a follow-up.)

Read before starting:

- `README.md` — the IP datasheet: features, unsupported features (§1.2), clock domains (§2.1), generics (§2.2), port tables
  (§2.3), programming sequence (§3.2.3), VHDL language rules (§3.2.4), directory overview (§4.1), **known issues (§4.4)**.
- `sim/README.md` — cocotb / Questa environment and how to run scenarios.
- `doc/spacefibre_light_top.md`, `doc/sfp_lane_configuration.md` — top-level entity doc; GTY channel-change procedure.
- The GitHub issues on `CNES/spacefibrelight` — the analysis (waveform captures, ECSS clause references) lives there.
- **ECSS-E-ST-50-11C** — the standard the clause numbers refer to.

## Workflow Overview

```
1) Understand   → issue, standard clause / README section, expected behaviour, layer, targets, twin module
2) Plan         → RTL approach (ports, CDC, FSM, target impact) + which scenario steps prove it      [CHECKPOINT]
3) Implement    → bug: failing scenario step first                                                  [CHECKPOINT]
                  RTL + file lists + scenario / bench updates, affected scenario green on both targets [CHECKPOINT]
4) Hand off     → full regression on VERSAL and NG_ULTRA, VHDL-93 check, existing docs updated
                  if affected, commits + PR text drafted                                              [FINAL CHECKPOINT]
```

Scale the steps to the change. For a small fix, steps 1 and 2 can be a single short message. The fixed part is the set
of checkpoints, not the amount of text:

- **No RTL before the user has agreed on the problem and the approach** (end of step 2).
- **Bug fixes: show the failing reproduction before touching RTL** (start of step 3).
- **Nothing is committed, pushed, posted, or opened without explicit approval**: commits, branches, issue comments, new
  issues, PRs. Draft the text, show it, and wait.

Track progress with a short checklist in the conversation (not on disk).

Hardware validation (VEK280 with STAR-Ultra / STAR-Fire equipment, `implementation/app/`) is done by the user.
NG-Ultra has **no** physical validation (README §1.1), so simulation is the only evidence for it.

---

## Repository Map

```
spacefibrelight/
├── src/
│   ├── pkg_tools.vhd                  # generic helper functions (log2, or_all, sat, ...)      → lib commun / data_link_lib
│   ├── pkg_data_link.vhd              # package data_link_lib (constants C_*, types)            → lib data_link_lib
│   ├── pkg_phy_plus_lane.vhd          # Versal phy+lane package                                  → lib phy_plus_lane_lib
│   ├── pkg_phy_plus_lane_64b.vhd      # NG-Ultra phy+lane package                                → lib phy_plus_lane_64_lib
│   ├── module_data_link/              # Data Link layer (shared by both targets, 32-bit)         → lib data_link_lib
│   ├── module_phy_plus_lane/          # Phy+Lane layer, VERSAL (32-bit, GTY)                     → lib phy_plus_lane_lib
│   ├── module_phy_plus_lane_64b/      # Phy+Lane layer, NG_ULTRA (64-bit, HSSL), files ppl_64_*  → lib phy_plus_lane_64_lib
│   ├── ip_spacefibre_light_top/       # top (spacefibre_light_top), Vivado wrapper (_ip), mux/demux, reset_gen
│   └── ip/                            # fifo_dc, AXIS<->custom FIFOs, fifo_dc_drop_bad_frame, vendor cores
├── sim/
│   ├── benches/configuration_2_bench/ # current cocotb top: IP + RTL models (configuration_1 is legacy)
│   ├── benches/common/                # common.py (TB base class), pkg_model.vhd (bench register map)
│   ├── models/                        # RTL generator/analyzer/configurator models + python SpaceFibre models
│   ├── scenario/                      # one folder per cocotb scenario, RunSim.sh, Makefile, compile_sim_lib.tcl
│   ├── cocotb-framework/              # git submodule (Elsys-Design DIGITAL-VERIFICATION-COCOTB)
│   └── libraries/                     # Xilinx simulation libraries (unisim, xpm, secureip, cores) — some via git-lfs
├── implementation/                    # board projects: app/ (VEK280 designs), board/NgUltra/create_project.py
├── xilinx_ip/spacefibrelight_full_wrapper/component.xml   # Vivado IP-packager definition
├── .linty/                            # linty.properties + yosys/read.ys
└── doc/                               # entity docs + assets (svg/png)
```

### Two targets, one IP

`G_TARGET` (`"VERSAL"` or `"NG_ULTRA"`) selects the phy+lane implementation inside `spacefibre_light_top`. The Data Link
layer is shared. The phy+lane layer exists **twice**, with parallel modules:

| Versal (`module_phy_plus_lane/`) | NG-Ultra (`module_phy_plus_lane_64b/`) |
| --- | --- |
| `lane_init_fsm.vhd` | `ppl_64_lane_init_fsm.vhd` |
| `lane_ctrl_word_detect.vhd` | `ppl_64_lane_ctrl_word_detect.vhd` |
| `lane_ctrl_word_insert.vhd` | `ppl_64_lane_ctrl_word_insert.vhd` |
| `rx_sync_fsm.vhd` | `ppl_64_rx_sync_fsm.vhd` |
| `skip_insertion.vhd` | `ppl_64_skip_insertion.vhd` |
| `parallel_loopback.vhd` | `ppl_64_parallel_loopback.vhd` |
| `phy_plus_lane.vhd` | `phy_plus_lane_64b.vhd` (+ `ppl_64_init_hssl`, `_word_alignment`, `_bus_concat_tx`, `_bus_split_rx`, `_rx_wr_en_fifo`) |
| `mib_phy_plus_lane.vhd` (shared by both targets) | |

**Every lane-layer change must be assessed for the twin module.** Precedent: issue #33 fixed the Versal lane init FSM and
opened #34 to repeat the analysis on NG-Ultra. If the twin is not changed, say why in step 2 and propose a follow-up issue
(created only with the user's approval).

| Clock | Domain | Versal | NG-Ultra |
| --- | --- | --- | --- |
| `CLK` | Data Link layer, Injector/Spy, MIB discretes | 150 MHz | 78.125 MHz |
| `CLK_TX` | Phy+Lane layer (from transceiver) | 150 MHz | 78.125 MHz |
| `CLK_HSSL` / `CLK_REF_*` / `CLK_GTY` | transceiver reference | 100 MHz | 100 MHz |
| `AXIS_ACLK_TX_DL(i)` / `AXIS_ACLK_RX_DL(i)` | per-VC AXI4-Stream, 9 each (8 VC + broadcast) | 150 MHz | 78.125 MHz |

---

## Conventions (extracted from the code base)

There is no convention document. Follow these rules, and when a file deviates, **match the surrounding file** rather than
reformatting it. Do not mix style clean-ups into functional changes.

### File header

Every VHDL source starts with the CNES CERN-OHL-W v2 banner, then the project block:

```vhdl
-----------------------------------------------------------------------------------
-- #                          Copyright CNES <year>                               #
-- #                                                                              #
-- # This source describes Open Hardware and is licensed under the CERN-OHL-W v2. #
-- #                                                                              #
-- # You may redistribute and modify this documentation and make products         #
-- # using it under the terms of the CERN-OHL-W v2 (https:/cern.ch/cern-ohl).     #
-- #                                                                              #
-- # This documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED             #
-- # WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY                 #
-- # AND FITNESS FOR A PARTICULAR PURPOSE.                                        #
-- #                                                                              #
-- # Please see the CERN-OHL-W v2 for applicable conditions.                      #
-----------------------------------------------------------------------------------
----------------------------------------------------------------------------
-- Author(s) : <initial. NAME>
--
-- Project : IP SpaceFibreLight
--
-- Creation date : <DD/MM/YYYY>
--
-- Description : <one or two sentences>
----------------------------------------------------------------------------
```

Copy the banner byte-for-byte from an existing file (e.g. `src/module_data_link/data_seq_compute.vhd`). Python scenario
files use the `## COMPANY : CNES / ## TITLE / ## PROJECT : SPACE FIBRE LIGHT / ## AUTHOR / ## CREATED / ## DESCRIPTION`
block (see any `sim/scenario/*/*.py`).

### Naming

| Item | Rule | Example |
| --- | --- | --- |
| File / entity | lower snake case, file name = entity name. Data link: `data_<function>`; Versal lane: `lane_<function>` / `<function>`; NG-Ultra: `ppl_64_<function>`; MIB: `mib_<layer>` | `data_seq_compute`, `ppl_64_rx_sync_fsm` |
| Architecture | `rtl` for synthesizable code | `architecture rtl of data_mac is` |
| Generic | `G_` + UPPER_SNAKE | `G_VC_NUM`, `G_TARGET` |
| Constant | `C_` + UPPER_SNAKE, shared ones in the layer package | `C_DATA_LENGTH`, `C_SIF_WORD` |
| Port | UPPER_SNAKE **suffixed with the abbreviation of the module that produces the signal**. Inputs carry the source module's suffix, outputs carry the own module's suffix | in `data_seq_compute`: `LINK_RESET_DLRE` (in, from data_link_reset), `DATA_DSCOM` (out) |
| Port group | comment `-- <module_name> (<ABBR>) interface` above each group | `-- data_encapsulation (DENC) interface` |
| Internal signal | lower snake; `_i` = internal copy of an output port; `_r` / `_rr` = registered / double-registered; `_n` = active low | `link_reset_dlre_i`, `lane_active_ppl_r`, `reset_gen_rr_n` |
| Process | label `p_<name>`, closed with `end process p_<name>;` | `p_seq_num_comp` |
| FSM | type `<name>_fsm` or `<name>_fsm_type`; states UPPER + `_ST`, each with a `--!` comment; state signal `current_state` | `CHECK_FAR_END_RST_ST` |
| Library | one library per layer (see Repository Map); the data link package is `data_link_lib.data_link_lib` | `use data_link_lib.data_link_lib.all;` |

Existing module abbreviations (reuse them; pick a new unique one for a new module and declare it in the group comment):

| Abbr | Module | Abbr | Module |
| --- | --- | --- | --- |
| `DL` | data_link (layer boundary) | `PPL` | phy_plus_lane |
| `DMAC` | data_mac | `MIB` | mib_* (management / discrete signals) |
| `DENC` | data_encapsulation | `NW` | network layer (AXI-Stream user side) |
| `DSCOM` | data_seq_compute | `DLRE` | data_link_reset |
| `DCCHECK` | data_crc_compute / data_crc_check (shared, historical) | `DERRM` | data_err_management |
| `DSCHECK` | data_seq_check | `DWI` | data_word_id_fsm |
| `DDES` / `DDESBC` | data_desencapsulation / _bc | `DIBUF` / `DIBUFBC` | data_in_buf / data_in_bc_buf |
| `DOBUF` | data_out_buf | `DMBUF` / `DMBUFBC` | mid buffers |
| `LCWI` / `LCWD` | lane_ctrl_word_insert / _detect | `RSF` | rx_sync_fsm |

### Comments and structure

- `--!` (TerosHDL / Doxygen style) comments on **every** port, generic, FSM state, and non-obvious signal.
- Section banners inside the architecture: `Signal declaration`, `Assignements`, `Process`, matching existing files.
- Each process gets a header block:
  ```vhdl
  ---------------------------------------------------------
  -- Process: p_<name>
  -- Description: <what it does>
  ---------------------------------------------------------
  ```
- **Standard references:** tag the line that implements a standard clause with `--!Req: <clause>` (e.g.
  `--!Req: 5.5.2.6.f.2`). Tag a known gap with `--FIXME missing !Req: <clause> <what is missing>`, as in
  `lane_init_fsm.vhd`. These tags are the repository's only in-code traceability mechanism; use nothing else.
- Spaces only, no tabs (several commits are "remove tab" / "clean up tab").
- Do not leave `attribute MARK_DEBUG` (Xilinx ILA) on new signals in merged code (precedent: "remove mark debug (unused)").

### Language: VHDL-93 compatible

README §3.2.4 promises that the sources compile as **VHDL-93 or VHDL-2008**. The one VHDL-2008 construct in the top
(`elsif ... generate`) was commented out for that reason (issue #37). New and modified synthesizable code **must stay
VHDL-93 compatible**. Do not use:

- `process (all)`
- `if ... elsif/else generate`, `case ... generate`
- conditional or selected signal assignment **inside** a process (`x <= a when c else b;` in a process)
- reading an `out` port inside the architecture (use an `_i` signal, the house pattern)
- unary reduction operators (`or vec`), matching operators (`?=`, `?/=`), `to_string`, `std_logic_vector` arithmetic
  from `numeric_std_unsigned`, external names

Use `pkg_tools` functions (`or_all`, `and_all`, `log2`, ...) instead. Use `ieee.numeric_std`; do not add new uses of
`std_logic_unsigned` / `std_logic_arith` (they only appear in the stale unit testbenches).

### Design style

The code base uses **single clocked processes** with explicit FSM `case` statements, not records or the two-process
style. Keep that style; do not convert existing modules. For a new module, use the same style unless the user explicitly
asks otherwise.

- **Resets.** `RST_N` is the system reset: active low, asynchronous assert (`process (CLK, RST_N)` /
  `if RST_N = '0' then ... elsif rising_edge(CLK) then`). Most RTL processes (82 of 106) use this form. Protocol resets
  (`LINK_RESET_*`, `LANE_RESET_*`, `INTERFACE_RESET`) are **synchronous functional inputs**, not system resets. Do not
  repeat the pattern flagged in `data_word_id_fsm.vhd` ("link reset is a command it is not supposed to be a system
  reset"). A new module takes `RST_N` for reset and treats link / lane reset as ordinary synchronous inputs.
- **Reset every register** assigned in the clocked branch inside the reset branch. Unreset registers in an async-reset
  process infer clock-enable logic, and NX synthesis has produced latches from this (see the workaround comment in
  `data_link_reset.vhd`).
- **No latches** (issue #13). Avoid combinational processes. Where one is unavoidable, assign every output on every path.
  A synthesis latch warning is a bug.
- **FSMs.** Enumerated type, `case current_state is` in a clocked process, and a `when others =>` branch that returns to
  the reset state for new FSMs (safe recovery matters for space use).
- **Generics.** `G_VC_NUM` range is 1–8. New code must elaborate for the whole range and must not make issue #21
  (`G_VC_NUM = 1` does not synthesize) worse. Size vectors from `G_VC_NUM`, not from literals.
- **Technology independence.** The IP is "designed to be as technology-independent as possible" (README §1.1). Vendor
  primitives (unisim, xpm, nx) belong **only** inside the target-specific phy+lane modules and `src/ip/cores/`. Never
  instantiate `xpm_cdc_*` or other vendor macros in the Data Link layer or other shared code: it breaks NG-Ultra.
- **Resource budget.** This is a *light* IP (README §2.5: ~4.9k FF / 5.1k LUT / 6.5 BRAM for 8 VCs on Versal). Call out
  any change that adds a BRAM or scales with `G_VC_NUM`.

### Clock domain crossing

The repository does not use Open Logic. Reuse the in-repo patterns:

| Signal type | Use | Reference |
| --- | --- | --- |
| Single-bit level (status, enable) | Two-flop synchronizer in the destination clock, `_a` → `_a_r` naming | `no_signal` in `module_phy_plus_lane/phy_plus_lane.vhd` |
| Reset release | async assert, sync double-register release | `ip_spacefibre_light_top/reset_gen.vhd` |
| Data stream / multi-bit | dual-clock FIFO | `src/ip/fifo_dc`, `FIFO_DC_AXIS_S` / `FIFO_DC_AXIS_M` |
| Frame stream with drop on error | dual-clock FIFO with bad-frame drop | `src/ip/fifo_dc_drop_bad_frame` |
| Single-cycle pulse, slow multi-bit status | **no in-repo block**: propose toggle + 2-FF or handshake in step 2 and ask | — |

Rules:

- Never pass an unsynchronized signal between `CLK`, `CLK_TX`, and the per-VC AXIS clocks.
- Never two-flop a multi-bit bus. Use `fifo_dc` or a handshake.
- Signals from the transceiver IP that the vendor documents as asynchronous (e.g. GTY `rxelecidle`, AMD AM002) are
  asynchronous, whatever clock they appear to come with.
- Adding a new external dependency (Open Logic, vendor CDC macros in shared code) is a decision for the user and the
  CNES maintainers. Propose it with trade-offs in step 2; never add it silently.

### Hierarchical names are an interface

cocotb scenarios reach into the hierarchy, e.g.
`tb.dut.spacefibre_instance.gen_inst_phy_plus_lane.inst_phy_plus_lane.RST_TX_DONE`, and every scenario has
`wave_versal.do` / `wave_ngultra.do` with hundreds of hierarchical paths. **Renaming an instance, generate label, or
signal breaks simulations.** This is why issue #37 keeps the VHDL-2008 `elsif generate` commented out. Before renaming,
run:

```bash
grep -rn "<old_name>" sim/scenario sim/benches sim/models
```

Then update every Python reference and both wave files in every scenario, or keep the old name.

### The four hand-maintained file lists

A new VHDL file, or a moved or renamed one, must be added in **all** of these, in dependency order (packages first),
with the correct library:

| File | Used by | Format |
| --- | --- | --- |
| `sim/scenario/compile_sim_lib.tcl` | every simulation | `vcom +cover=sb +acc -work <lib> $rootpath/src/...` (NG-Ultra 64b files use `-2008`) |
| `.linty/yosys/read.ys` | Linty CI | `verific -work <lib> -vhdl src/...` |
| `implementation/board/NgUltra/create_project.py` | NG-Ultra build | `getProject().addFile('<lib>', PROJECT_ROOT+'src/...')` |
| `xilinx_ip/spacefibrelight_full_wrapper/component.xml` | Vivado IP (Versal) | `<spirit:file>` entries. Generated by the Vivado IP packager: prefer repackaging with Vivado 2024.1; if hand-edited, copy an existing entry exactly and tell the user to re-validate in Vivado |

Bench-only VHDL (models, bench top) goes in `sim/scenario/Makefile` `VHDL_SOURCES` (library `work`).

---

## Step 1: Understand

Goal: agree on **what** is wrong or missing and what the correct behaviour is.

1. **Find the issue.** All work is tracked in the CNES issues. Read the issue with its comments, captures, and linked
   code lines:
   ```bash
   gh issue list -R CNES/spacefibrelight --state all
   gh issue view <n> -R CNES/spacefibrelight --comments
   ```
   If there is no issue, draft one in the style of the existing ones (short title; description with observation,
   expected behaviour, clause reference, code link) and show it to the user. Create it only on explicit approval.
2. **Check what is already documented.** README §4.4 (Known issues) and §1.2 (Unsupported features): the behaviour may
   be a known, accepted limitation.
3. **Pin down the reference behaviour.** Name the ECSS-E-ST-50-11C clause(s) involved, by clause number, as the issues and
   `--!Req:` tags do. For behaviour the standard does not cover (Injector/Spy, discrete QoS / error-management signals,
   target specifics), the reference is the README section describing it. If neither covers it, say so and ask the user
   what the intended behaviour is. Do not make one up.
4. **Locate it.** Layer (Data Link / Lane Versal / Lane NG-Ultra / top / MIB / bench), targets affected, twin module, and
   the closest comparable code or earlier fix.

For a bug, state **observed vs expected** behaviour with the evidence (issue capture, scenario log).

Ask back whenever there is a real choice (fix here or upstream, full compliance or accepted gap, both targets now or a
follow-up), rather than deciding silently.

## Step 2: Plan

Goal: agree on **how** before any code exists. Present in the conversation, sized to the change:

- **RTL approach:** which modules and processes change and why. For a port or generic change, the before / after list.
  For a new module, the entity declaration in house style. Flag any change to `spacefibre_light_top` ports or
  generics: it touches README §2.2 / §2.3, `doc/spacefibre_light_top.md`, `spacefibre_light_top_ip.vhd`,
  `component.xml`, and the bench.
- **Where it sits** in the pipeline (`data_mac → data_encapsulation → data_seq_compute → data_crc_compute → mux_tx → PPL`
  on TX; the reverse on RX) and every **clock-domain crossing** with its mechanism from the CDC table. An ASCII sketch
  helps for anything beyond a one-process fix.
- **FSM changes:** states and transitions, with the clause for each changed transition.
- **Target impact:** twin module changed or not, and why.
- **Reuse:** existing blocks and `pkg_tools` functions instead of new logic.
- **Test approach:** which scenario (existing preferred, e.g. link reset behaviour → `data_link_link_reset`, or a new
  scenario folder) and the steps to add. For each step, the stimulus, the value checked, and the clause or README
  section it demonstrates. Include reset / error-injection / recovery cases and back-pressure for data-path changes
  when relevant. This list stays in the conversation. It is not written to a file.
- **Trade-offs** worth a decision: fix at the source vs the symptom (e.g. #41: throttle `data_mac` vs handle FIFO full
  in `data_crc_compute`); top-level interface change vs keeping it internal; new MIB discrete vs an existing status;
  resource cost.

### **CHECKPOINT — STOP**

Ask the user to challenge the approach, the CDC plan, the twin-module decision, and the test approach. **Wait for
explicit approval before writing code.**

## Step 3: Implement and Test

### 3a — Bugs: reproduce first

Add the scenario step(s) that exercise the bug and run them on the **current** code. They must fail in the way the issue
describes. This is the established pattern (Elsys "bug illustration scenario" on the #27 / #28 branches). **Show the
failing log to the user** before changing RTL, so both sides agree the reproduction matches the issue.

### 3b — RTL

Implement the approved plan following **Conventions**. Before presenting:

- [ ] Header banner present (new file); `--!` comments on every new port / generic / state.
- [ ] `--!Req:` tags on lines implementing clauses; `--FIXME missing !Req:` on accepted gaps.
- [ ] VHDL-93 compatible (no constructs from the forbidden list).
- [ ] `RST_N` async reset; all clocked registers reset; no combinational latches; new FSMs have `when others`.
- [ ] CDC as planned; no vendor primitive in shared code.
- [ ] Works for `G_VC_NUM` 1–8 (no hard-coded 8 / 9 widths).
- [ ] Twin lane module updated, or the follow-up agreed with the user.
- [ ] No renamed hierarchy used by `sim/` (or all references updated).
- [ ] New or moved files registered in all four file lists (+ `sim/scenario/Makefile` for bench-only files).
- [ ] No leftover `MARK_DEBUG`, tabs, commented-out experiments, or unrelated reformatting.

### 3c — Scenario

#### Scenario anatomy

```
sim/scenario/<scenario_name>/
├── <scenario_name>.py                                     # cocotb module: folder name == module name (RunSim.sh sets MODULE)
├── extended_phy_layer_gtwiz_versal_0_0_gt_quad_base_0.mem # GTY quad config for VERSAL: copy from an existing scenario
├── wave_versal.do                                         # loaded by vsim when HARDWARE_TARGET=VERSAL
├── wave_ngultra.do                                        # loaded by vsim when HARDWARE_TARGET=NG_ULTRA
└── stimuli/
    ├── axi/*.json                                         # AXI-Lite sequences: tb.masters[i].init_run("stimuli/axi/x.json")
    └── spacefibre_serial/*.dat                            # serial word streams: tb.spacefibre_driver.write_from_file(...)
```

Every existing scenario has all five parts: vsim is launched with `-do wave_<target>.do` (see `sim/scenario/Makefile`)
and the Versal GTY model loads the `.mem` file from the run directory, so keep all of them. Prefer adding steps to an
existing scenario. For a new one, copy the closest existing scenario (short template:
`lane_status_and_parameters_access`, 224 lines; data-link template: `data_link_link_reset`) and trim it.

Verification is **system-level**: scenarios drive the whole IP on `configuration_2_bench`. The per-module unit
testbenches in `src/*/tb/` are stale (README §4.4.4, issue #6; their compile scripts point at pre-refactor paths). Do
not rely on them, and do not build new unit-test infrastructure unless the user asks for it.

#### Code pattern

Keep the house structure so results read like every other scenario:

- Import `TB` and the register `Data_read_*` objects from `tb2`, guarded by the existing `try: import framework` block.
- One `@cocotb.test() async def cocotb_run(dut)`. It builds `tb = TB(dut)`, runs `await tb.reset()`, then runs the
  numbered steps. Each step starts with the banner comment `Step N: <title>` and logs sub-steps `N.M` as
  `step N.M result: Pass` or `... Failed` with the simulation time.
- Reuse helper coroutines already written in the scenarios (`initialization_procedure`, `init_lane`, `send_FCT`,
  `send_ACK`, `send_NACK`, `send_idle_ctrl_word`, `get_resetflag`, ...) instead of rewriting them.
- **Checks compare values, not just arrival:** sink monitor words, register fields read over AXI-Lite, received
  AXI-Stream data.
- End with a results summary per step, then `raise TestFailure` if anything failed.
- **Every step's failure flag must set the global `test_failed`.** Existing scenarios do not always do this: in
  `data_link_link_reset.py`, `step_2_failed` is only logged, so a step-2 failure still passes the test. New steps must
  propagate. If you find a non-propagating flag in a scenario you touch, point it out to the user.
- cocotb is pinned to **1.9.x** (`from cocotb.result import TestFailure`, `get_sim_time(units=...)`). Do not use
  cocotb 2.x APIs.

#### Observing new signals

Scenarios read IP status through the bench configurator over AXI-Lite (`S_CON_AXI`). The register map is:

| Offset | Object in `tb2.py` | Content |
| --- | --- | --- |
| `0x00` | `Data_read_general_control` | global control (reset, enable inj/spy) |
| `0x04` | `Data_read_phy_config_parameters` | phy parameters |
| `0x08` | `Data_read_lane_config_parameters` | lane parameters (LaneStart, AutoStart, ...) |
| `0x0C` | `Data_read_lane_config_status` | lane status (`LANE_STATE` in bits [3:0]) |
| `0x10` | `Data_read_dl_config_parameters` | data link parameters |
| `0x14` / `0x18` | `Data_read_dl_config_status_1/2` | data link status |
| `0x1C` / `0x20` | `Data_read_dl_config_QoS_1/2` | QoS discretes |
| `0x24` | `Data_read_dl_config_err_mngt` | error-management discretes |

Constants are in `sim/benches/common/pkg_model.vhd` (`C_ADDR_DL_*`). Decoding is in
`sim/models/data_link/data_link_configurator/data_link_configurator.vhd`. To expose a new discrete: wire it in
`configuration_2_bench.vhd` and map it into a free bit of the right register in the configurator (or add a register, a
`C_ADDR_*` constant, and a `Data_read_*` object in `tb2.py`). Internal signals can also be probed hierarchically from
Python. That is acceptable for checks, but it couples the test to names (see "Hierarchical names are an interface").

#### Keep wave files in sync

If the RTL change adds, removes, or renames signals that appear in `wave_versal.do` / `wave_ngultra.do`, update the wave
files of **every** scenario (issue #8 is the backlog from not doing this).

### 3d — Run the affected scenario on both targets

See "Environment" and "Running" under step 4. Run the new or changed scenario with `HARDWARE_TARGET="VERSAL"` and
`"NG_ULTRA"`. For a bug, the step that failed in 3a must now pass.

### **CHECKPOINT — STOP**

Present the diff (`git diff`) grouped by file with a one-line rationale per hunk, the file-list updates, any
bench / model / register-map changes, and the scenario logs on both targets. **Wait for explicit approval.**

## Step 4: Regress and Hand Off

### Environment

Detect what is available before promising a result:

```bash
command -v vsim                                   # Questa / ModelSim (sim/README lists Questa Intel Starter FPGA 2023.2 and Questa 2024.3)
cocotb-config --version                           # expect 1.9.x
python -c "import cocotbext.axi"                  # cocotbext-axi
git submodule status sim/cocotb-framework         # leading '-' => run: git submodule update --init
git lfs ls-files | head                           # large Xilinx models (secureip, unisim) must be present, not pointers
```

Questa is the **only** supported simulator (the flow uses its own `Makefile.questa`; GHDL / NVC do not work: vendor
Verilog/SystemVerilog models, FLI). If `vsim` is missing, say so plainly and stop at "RTL compiled / not simulated". Never
report tests as passing without a run log.

Create `sim/scenario/environnement` (git-ignored, French spelling as used by `RunSim.sh`):

```bash
export SPACEFIBRELIGHT_ROOT_PATH=/abs/path/to/spacefibrelight
export FRAMEWORK_COCOTB_INSTALL_PATH=$SPACEFIBRELIGHT_ROOT_PATH/sim/cocotb-framework/src
export GUI=0
export WAVES=0                      # 1 => vsim.wlf for debugging
export HARDWARE_TARGET="VERSAL"     # or "NG_ULTRA"
# export EXTRA_VSIM_CMD="-do $SPACEFIBRELIGHT_ROOT_PATH/sim/scenario/custom.do"
```

### Running

```bash
cd sim/scenario
./RunSim.sh <scenario_name>     # single scenario
./RunSim.sh all                 # every scenario folder except archive/ and covhtmlreport/
```

Run `all` with `HARDWARE_TARGET="VERSAL"`, then again with `HARDWARE_TARGET="NG_ULTRA"`. Runs are long: start them in
the background and monitor them rather than blocking. `RunSim.sh all` neither stops on failure nor prints a summary,
so collect the results yourself after each target:

```bash
for r in */results.xml; do
  if grep -q "<failure" "$r"; then echo "FAIL  ${r%/results.xml}"; else echo "PASS  ${r%/results.xml}"; fi
done
```

Also scan `*/questa_vhdl_compile_log.dat` and `*/questa_simulation_log.dat` for errors and new warnings (latch, width
mismatch, unbound component). The seed is fixed (`RANDOM_SEED = 123456789` in `sim/scenario/Makefile`), so results are
deterministic. A failure that "goes away" on re-run is not acceptable.

**Regression rule:** every scenario passes on both targets before a PR is proposed. If a scenario was already failing on
`develop` before the change, prove it by running it on a clean `develop` checkout and report it separately. Never hide it.

### VHDL-93 compatibility check

From a scenario folder that has just run (its `modelsim.ini` maps the libraries), recompile each new or changed
synthesizable file in VHDL-93 mode into its library:

```bash
cd sim/scenario/<scenario_name>
vcom -93 -work <library> $SPACEFIBRELIGHT_ROOT_PATH/src/<path>/<file>.vhd
```

Any error means a VHDL-2008 construct slipped in. (Files already compiled with `-2008` in `compile_sim_lib.tcl`, the
NG-Ultra `ppl_64_*` modules and the vendor HSSL wrapper, are exempt, but do not add new 2008-only constructs to them.)

### Synthesis and Linty

- **Linty** runs on push to the CNES repository and reports to the SonarQube dashboard (README badge). It needs secrets,
  so on a fork the workflow is expected to fail or produce no report. There is no local equivalent without a Linty
  license: apply the rules manually (latches, resets, unused signals, naming) and ask the user to check the quality gate
  after the PR.
- **Synthesis** (Vivado 2024.1 for Versal via `implementation/app/*/create_project.tcl`; NanoXplore Impulse for NG-Ultra
  via `implementation/board/NgUltra/create_project.py`) is usually run by the user. If available, check for latch
  warnings and resource changes.

### Existing documentation — update only if the change affects it

Do **not** create new documentation files, sections, or diagrams. Only correct what the change makes wrong or
incomplete:

| If the change... | update |
| --- | --- |
| changes top-level ports or generics | README §2.2 / §2.3 tables, `doc/spacefibre_light_top.md` (plus the code in `spacefibre_light_top_ip.vhd` and `component.xml`) |
| changes behaviour described in the README | the paragraph that describes it (README §3, programming sequence §3.2.3) |
| fixes a listed known issue | its README §4.4 entry (remove or adjust) |
| leaves or introduces a standard gap the user wants recorded | a README §4.4 entry in the same style as the existing ones, and `--FIXME missing !Req:` in code |
| changes the resource figures noticeably (user-measured) | README §2.5 |

Anything else (new module internals, design rationale, test descriptions) stays in the code comments, the commit
messages, and the PR.

### Branch, commits, PR (only with explicit approval)

- **Branch** from `develop`, named after the issue: `<issue#>-<slug>` (GitHub's "create branch" default, e.g.
  `36-unknown-data-value-are-sent-by-spacefibrelight`). Use `feat/<name>` / `bug/<name>` only for work without an issue.
- **Commits:** small and focused, short lower-case imperative messages (`fix SIF for IDLE`, `add CDC for no_signal`).
  Each commit should compile. Do not commit `sim_build/`, `results.xml`, logs, `*.vstf`, `environnement`, or
  `custom.do` (check `git status`; a `vsim_stacktrace.vstf` has already slipped into `data_link_transmission/` once).
- **PR** against `CNES/spacefibrelight:develop` (from a fork: `gh pr create -R CNES/spacefibrelight --base develop`).
  Title = issue title (e.g. `36 unknown data value are sent by spacefibrelight`) or a short description. Body: the
  house-style short bullet list of what changed, as in PRs #39–#42. No added report sections or tables. Never target
  `main`: maintainers merge `develop` → `main` as versioned releases ("V0.x : ...").

### **FINAL CHECKPOINT**

Report to the user in the conversation: regression result per scenario and target, the VHDL-93 check, any doc edits, the
drafted commit messages and PR text, and an explicit list of what was **not** verified (hardware, Linty, synthesis).
Commit, push, and open the PR only on the user's go-ahead.

---

## Where to Start

When modifying existing code, **do not jump to RTL.** The README is the datasheet of record: if README and code disagree,
either the code is wrong or the README must be corrected in the same PR. Decide which with the user.

| Change type | Steps |
| --- | --- |
| Bug fix | 1 (short) → 2 (short) → 3a reproduce → 3b–3d → 4 |
| Standard clause newly implemented / FSM change | 1 → 2 → 3 → 4 |
| New module or top-level port / generic change | 1 → 2 (full) → 3 → 4 (docs + Vivado IP affected) |
| New test steps only | 2 (test approach) → 3c–3d → 4 |
| Bench / model / stimuli fix | 1 → 2 → 3c–3d → 4 (state clearly that the DUT is unchanged) |
| Documentation-only correction | edit the affected README / doc section; no regression needed |

## Debugging Principle: Test Infrastructure First

When a scenario fails, investigate in this order before touching the DUT:

1. **Environment:** submodule and git-lfs files present, correct `HARDWARE_TARGET`, stale `sim_build/` (RunSim.sh
   deletes it, a manual `make` does not), cocotb 1.9.x.
2. **Stimuli and models:** `.dat` word streams (running disparity, K-codes), JSON register sequences, Python
   driver / sink / random generator, RTL generator / analyzer models. README §4.4.3 lists the models as a suspected
   source of the robustness issue.
3. **Bench wiring and register map:** `configuration_2_bench.vhd`, configurator bit positions, `tb2.py` offsets.
4. **Hierarchical references:** Python paths and wave files after RTL renames.
5. **DUT:** only after ruling out 1–4.

Use `WAVES=1` to dump `vsim.wlf`. The `wavequery.py` tool from the `fpga-module-dbg` skill can query WLF / VCD from the
command line. Remember that the IP has an inherent RX processing latency: word misalignment between the near-end and
far-end captures is expected (issue #33 discussion).

## When NOT to use this skill

- Board / application projects under `implementation/app/` (Vivado block designs, R5 software).
- Linty / GitHub Actions / gh-pages workflow changes.
- Pure documentation typo fixes.
- Questions about the codebase that do not lead to a change. Answer them directly.

## Reference examples

| Pattern | Reference |
| --- | --- |
| Small clocked data-path stage, producer-suffix ports | `src/module_data_link/data_seq_compute.vhd` |
| FSM with ECSS clause tags and gaps | `src/module_phy_plus_lane/lane_init_fsm.vhd` (cleaned in #33), `src/module_data_link/data_link_reset.vhd` |
| Single-bit CDC of an asynchronous transceiver signal | `no_signal` in `src/module_phy_plus_lane/phy_plus_lane.vhd` |
| Reset synchronizer | `src/ip_spacefibre_light_top/reset_gen.vhd` |
| Dual-clock FIFO | `src/ip/fifo_dc/fifo_dc.vhd` |
| Short scenario template | `sim/scenario/lane_status_and_parameters_access/` |
| Data-link scenario with reset / FCT / ACK helpers | `sim/scenario/data_link_link_reset/` |
| Issue → branch → PR flow | PR #42 (issue #36), PR #35 (issue #33), PR #39 (issue #13) |

When starting, **always** open the closest reference first and mirror its structure, header, and comment style.
