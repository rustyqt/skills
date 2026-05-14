---
name: open-logic-dbg
description: Debug failing or unexpected Open Logic VUnit testbenches by analysing the simulator log, capturing waveforms, and querying signal data with the wavequery tool. Use when a VUnit test fails, a simulation produces unexpected results, or the user asks to debug, troubleshoot, or investigate an Open Logic entity, testbench, or simulation issue.
---

# Open Logic — Test-Failure Debugging Workflow

Base directory for this skill: the **Open Logic repository root** (where `sim/run.py` lives).

This skill guides debugging of failing or misbehaving Open Logic simulations. It uses an iterative
**diagnose → fix → re-verify** loop and reuses the development phases from
[`open-logic-dev`](../open-logic-dev/SKILL.md) when picking the right place to fix.

## Debugging Principles

### 1. Never guess — diagnose first

Every fix must be preceded by a root-cause analysis that identifies **what** is wrong and **why**.
A wrong diagnosis leads to fixes that mask the real problem or introduce new ones.

### 2. Investigation priority order

When a VUnit test fails, look at the layers in this order — start at the cheapest and walk outward
only if the previous layer is innocent:

1. **VUnit log itself** — `check_equal` mismatch, watchdog timeout, assertion text, line/file pointer.
2. **Testbench logic** — wrong stimulus, wrong expected value, missing wait, mis-aligned latency assumptions.
3. **VUnit verification-components configuration** — `stall_config` for `axi_stream_master_t` / `axi_stream_slave_t`,
   `tuser` width mismatches, time-out values inside `check_axi_stream` / `pop_axi_stream`.
4. **Test harness wiring** — generic mapping, port mismatches, undriven signals, missing clocks.
5. **RTL bugs** — only after the previous layers are ruled out. Look at the FSM, datapath, control signals.

### 3. Fix at the right development phase

Every fix maps back to a phase from [`open-logic-dev`](../open-logic-dev/SKILL.md). Identify the
root-cause category, then update from that phase forward:

| Root cause                                        | Fix in phase | Files touched |
| ------------------------------------------------- | ------------ | ------------- |
| Wrong / missing interface decision                | Phase 1      | RTL entity declaration → all downstream files |
| RTL implementation bug                            | Phase 2      | `src/<area>/vhdl/...` (+ TB re-run) |
| Missing test coverage (entity correct, TB blind)  | Phase 3      | `test/<area>/<entity>/<entity>_tb.vhd` (+ `sim/test_configs/olo_<area>.py`) |
| VC / BFM config issue                             | Phase 3      | TB only |
| Documentation out of sync with new behaviour      | Phase 4      | `doc/<area>/<entity>.md` |
| Compile-order / Changelog miss                    | Phase 5      | `compile_order.txt`, `Changelog.md` |

Do **not** fix RTL to work around a testbench bug. Do **not** fix the testbench to hide an RTL bug.

---

## The Diagnose-Fix-Verify Loop

```
+-----------------------------+
| 1. RUN FAILING TEST         |
|    Capture full log         |
+--------------+--------------+
               |
               v
+-----------------------------+
| 2. ANALYSE LOG              |
|    Identify failure point   |
|    Extract expected vs got  |
+--------------+--------------+
               |
        Root cause clear?
       yes /         \ no
          |           v
          |  +-----------------------------+
          |  | 3. WAVEFORM ANALYSIS        |
          |  |    Re-run with waves        |
          |  |    Query with wavequery.py  |
          |  +--------------+--------------+
          |                 |
          v                 v
+-----------------------------+
| 4. READ SOURCE              |
|    Confirm hypothesis from  |
|    log / waveform           |
+--------------+--------------+
               |
               v
+-----------------------------+
| 5. PICK FIX PHASE           |
|    (table above)            |
+--------------+--------------+
               |
               v
+-----------------------------+
| 6. APPLY FIX                |
+--------------+--------------+
               |
               v
+-----------------------------+
| 7. RE-RUN FAILING TEST      |
+--------------+--------------+
               |
          pass / fail
            |    \
           pass   fail → back to step 2
            |
            v
+-----------------------------+
| 8. RUN FULL ENTITY REGRESS. |
+-----------------------------+
```

---

## Pre-flight: pick a simulator that actually exists

Open Logic supports three simulators (see [`open-logic-dev`](../open-logic-dev/SKILL.md)
§"Simulator Support"). Detect what is installed before running anything:

```python
import shutil
sims = {
    name: shutil.which(binary)
    for name, binary in {"ghdl": "ghdl", "nvc": "nvc", "modelsim": "vsim"}.items()
    if shutil.which(binary)
}
```

Priority for the debug skill:

1. **GHDL** — fastest free path; matches the HDL-Check CI default. Produces VCD or GHW waveforms.
2. **NVC** — second free option; produces VCD or FST.
3. **ModelSim / Questa** — required for coverage; produces WLF (convert to VCD with `wlf2vcd` if needed).

Use `sim/run.py`'s flags accordingly:

```bash
cd sim
python run.py -p 4 "*<entity>*"                # default: GHDL
python run.py --nvc      -p 4 "*<entity>*"
python run.py --modelsim -p 4 "*<entity>*"
```

If no simulator is on PATH, point the user at `doc/HowTo.md` §"Run Simulations" and stop.

---

## Step 1: Run the failing test

Run the specific failing case verbosely so the full simulator log is captured:

```bash
cd sim
python run.py -v "*<entity>*<test_case>*"
```

Hints in the log to watch for:

- The VUnit pass/fail line at the very end (counts and failed-config names).
- The simulator-native assertion that triggered the failure (`Error: ...`, `Failure: ...`).
- The simulation time of the first error.
- VUnit `check_equal` lines: they print expected vs. got values and the source location.
- Watchdog hits: `test_runner_watchdog(runner, 1 ms)` reaching its limit means the TB is waiting for an event that never arrives.

### Common VUnit failure patterns

| Pattern | Meaning | Typical cause |
| --- | --- | --- |
| `check_equal => Got X, Expected Y` (with source `<file>:<line>`) | Direct value mismatch | RTL produces wrong output **or** TB expects wrong value |
| `Watchdog timeout` | TB never reached `test_runner_cleanup` | Stalled handshake, missing stimulus, frozen FSM, or watchdog too tight |
| `axi_stream slave : Expected … but got …` | VUnit VC mismatch | DUT output wrong, or wrong `expected` in `check_axi_stream` |
| `Simulation stopped due to error in file …` (GHDL/NVC) | Native VHDL assertion fired | `assert false report "…" severity failure;` inside RTL or TB |

If the log clearly identifies the root cause (e.g. obvious typo in the expected value), skip to Step 4.
Otherwise continue to Step 3 for waveform analysis.

---

## Step 3: Waveform Analysis with `wavequery`

The `wavequery` tool is at `.claude/skills/open-logic-dbg/wavequery.py`. It accepts VCD (from GHDL,
NVC, or `wlf2vcd`-converted Questa output) and exposes signal queries from the command line.

Install once: `python -m pip install vcdvcd`.

### 3a — Re-run the failing test with waveform capture

The capture flag is simulator-specific; the cleanest cross-tool recipe is:

```bash
cd sim
# GHDL: produce a VCD into the VUnit output tree
python run.py -v "*<entity>*<test_case>*" --gtkwave-fmt vcd

# NVC: same flag works (VUnit normalises it)
python run.py --nvc -v "*<entity>*<test_case>*" --gtkwave-fmt vcd

# Questa: produces a WLF by default; wavequery will convert it on demand if
# `wlf2vcd` is on PATH (ships with QuestaSim/ModelSim).
python run.py --modelsim -v "*<entity>*<test_case>*"
```

The output lands under `sim/vunit_out/<simulator>/test_output/<test-id>/`.

### 3b — Discover available signals

```bash
python .claude/skills/open-logic-dbg/wavequery.py \
    --test "*<entity>*<test_case>*" \
    list-signals --filter "*dut*"
```

Narrow with `--filter` until you have a manageable list.

### 3c — Targeted queries

**Signal value at a specific time:**
```bash
python .claude/skills/open-logic-dbg/wavequery.py \
    --test "*<entity>*<test_case>*" \
    value-at --signal "*<signal>*" --time <failure_time>
```

**All transitions of a signal in a window:**
```bash
python .claude/skills/open-logic-dbg/wavequery.py \
    --test "*<entity>*<test_case>*" \
    transitions --signal "*<signal>*" --from <before> --to <after>
```

**FSM trace with named states:**
```bash
python .claude/skills/open-logic-dbg/wavequery.py \
    --test "*<entity>*<test_case>*" \
    fsm --signal "*Fsm*" --names "Idle=0000,Run=0001,Done=0010"
```

**Find when a signal first transitioned:**
```bash
python .claude/skills/open-logic-dbg/wavequery.py \
    --test "*<entity>*<test_case>*" \
    find-edge --signal "*Rst*" --edge rising --nth 1
```

**Compare expected vs actual at multiple times:**
```bash
python .claude/skills/open-logic-dbg/wavequery.py \
    --test "*<entity>*<test_case>*" \
    compare --signal "*Out_Data*" --expect "1us=00FF,2us=DEAD"
```

Use `--format json` if you need to post-process the output.

### 3d — Investigation recipes

**Data-path mismatch:**
1. Check the FSM state at the failure time.
2. Check input handshake signals (`In_Valid` / `In_Ready`) — was the stimulus accepted on the expected cycle?
3. Check output handshake (`Out_Valid` / `Out_Ready`) — did the DUT actually present a beat?
4. Trace backward: find the cycle the value diverged from expected; check the producing logic at that cycle.

**Timeout / never-fires:**
1. Did the awaited signal ever transition? Run `transitions` over the whole sim.
2. If never: trace the upstream signal that should have driven it.
3. If yes but late: check whether the test's wait window is realistic for the entity's documented latency.

**CDC / intermittent failure:**
1. Identify the clock domains involved (look at `<Domain>_Clk` ports).
2. Check whether the suspect signal uses one of the `olo_base_cc_*` entities (every multi-bit CDC must use a proper crossing — see `doc/base/clock_crossing_principles.md`).
3. Re-run the test multiple times. CDC bugs may pass by luck.

---

## Step 4: Read the source

After the log + waveform points to a hypothesis, **read the relevant source** to confirm:

- **RTL bug:** open `src/<area>/vhdl/olo_<area>_<function>.vhd`. Trace from the failing output back through the combinational / sequential path. Compare against the description header.
- **TB bug:** open `test/<area>/<entity>/<entity>_tb.vhd`. Verify VC configuration (`new_axi_stream_master`, `new_axi_stream_slave`, `stall_config`), expected values, and `wait_until_idle` placement.
- **Architecture mismatch:** open `doc/<area>/<entity>.md` — if RTL behaviour disagrees with the doc, exactly one of them is wrong. Decide which is the source of truth (usually the RTL, but check `Changelog.md` to see whether the doc was supposed to change).

---

## Step 6: Apply the fix

Update at the phase identified in Step 5. Stay aware of downstream impact:

| Fix layer | Phases to re-touch |
| --- | --- |
| Interface change (port / generic) | re-do **all** of `open-logic-dev` Phase 1 (review with user) → RTL → TB → doc → integration. |
| RTL fix | RTL → re-run TB → update doc if behaviour changed. |
| TB fix only | TB only, then re-run. |
| Doc-only correction | doc only. |

---

## Step 7-8: Re-verify

```bash
# 1. The specific failing test must now pass
cd sim
python run.py -v "*<entity>*<test_case>*"

# 2. Full regression for the entity (catches regressions in sibling cases)
python run.py -p 8 "*<entity>*"

# 3. On the second free simulator if installed
python run.py --nvc -p 8 "*<entity>*"
```

If any step still fails, return to Step 2 and re-diagnose — the failure mode may have shifted.

---

## `wavequery.py` Reference

**Location:** `.claude/skills/open-logic-dbg/wavequery.py`
**Dependency:** `pip install vcdvcd`

### Global options

| Option | Description |
| --- | --- |
| `--test PATTERN` | VUnit test-name glob (e.g. `*olo_base_fifo*back-to-back*`) |
| `--vcd PATH` | Direct path to a VCD file |
| `--wlf PATH` | Direct path to a WLF file (auto-converts to VCD if `wlf2vcd` is on PATH) |
| `--vunit-out PATH` | Override the VUnit output directory (default: `sim/vunit_out/`) |
| `--format {table,json}` | Output format (default `table`) |

### Subcommands

| Command | Purpose |
| --- | --- |
| `list-tests` | List tests for which a WLF/VCD file exists |
| `list-signals` | List all signals (use `--filter <glob>` to narrow) |
| `value-at` | Get signal value(s) at specific time(s) |
| `transitions` | List transitions in a time range (`--from`, `--to`) |
| `find-edge` | Find the Nth rising/falling edge of a signal |
| `duration` | Measure how long a signal held a specific value |
| `compare` | Expected vs. actual at a list of times |
| `fsm` | State trace with named states |

### Time format

All time arguments accept: `100ps`, `200ns`, `1.5us`, `10ms`, `0.5s`. Plain integers = picoseconds.

### Signal patterns

Glob, case-insensitive. Use `*` for any path segment. Examples:
- `*dut*State*`
- `*i_dut/In_Valid`
- `*Out_*`

If a pattern matches multiple signals the tool reports them and asks for a narrower glob.

---

## Common Open Logic Failure Scenarios

### Scenario: AXI4-Stream back-to-back mismatch

1. `check_axi_stream` mismatch in the second or later beat.
2. Re-run with `--gtkwave-fmt vcd`.
3. `transitions` on `Out_Data` around the mismatch — typically a register update lags by one cycle.
4. Confirm `olo_base_pl_stage` (or whichever pipeline stage feeds the output) honours `Out_Ready` correctly.
5. If the master VC also stalls, set the slave VC stall_config to `(0.0, 0, 0)` temporarily to isolate.

### Scenario: Watchdog timeout

1. Watchdog hits in the test process — no `check_equal` failed yet.
2. Look at the last `info()` / `notice()` line in the log to see how far the test got.
3. Capture waves. Use `transitions` on the awaited signal across the whole sim — never asserted?
4. Trace upstream signals: is the entity stuck waiting for an internal handshake?
5. **Common open-logic-specific cause:** wrong reset polarity in the test — Open Logic resets are
   high-active synchronous; releasing too early can leave the FSM in an undefined state.

### Scenario: FSM stuck in wrong state

1. Test never reaches the expected output state.
2. Re-run with waves.
3. `fsm --signal "*Fsm*" --names "..."` from the entity's enum (see `_pkg.vhd` or the architecture file).
4. Identify where the FSM diverged.
5. Read the RTL state-machine code and compare against `doc/<area>/<entity>.md` §"Architecture".

### Scenario: Clock-domain-crossing bug (intermittent failure)

1. Test passes some runs, fails others.
2. Identify which signal crosses a domain — look at `<Domain>_Clk` ports in the entity declaration.
3. Verify the right `olo_base_cc_*` entity is used (see table in `open-logic-dev` Phase 2).
4. **Never** apply a 2-FF synchroniser to a multi-bit bus. Replace with `olo_base_cc_handshake` or `olo_base_fifo_async`.
5. Re-run several times after the fix — CDC bugs are statistical.

### Scenario: Coverage hole reported by Questa run

1. Only relevant when the user runs `python run.py --modelsim --coverage`.
2. Open `sim/AnalyzeCoverage.py` output — it lists uncovered lines / branches by source file.
3. For each hole: add a directed test case in the TB targeting the missing branch.
4. Register the new config in `sim/test_configs/olo_<area>.py` if it introduces a new generic value.
5. Re-run coverage; the badges (after a CI run on `main`) will update automatically.

---

## When NOT to use this skill

- **Adding a brand-new entity from scratch.** Use [`open-logic-dev`](../open-logic-dev/SKILL.md) — the six-phase workflow exists exactly for that purpose.
- **Pure documentation issues** (typo, broken link). Edit and run `markdownlint`.
- **Compile errors in user code** outside Open Logic. Wrong skill — point the user at the appropriate language server / lint output.
