---
name: fpga-module-dbg
description: Debug failing FPGA simulation tests by analyzing UVVM logs, capturing waveforms, and querying signal data with the wavequery tool. Use when a VUnit test fails, a simulation produces unexpected results, or the user asks to debug, troubleshoot, or investigate an FPGA module, testbench, or simulation issue. Covers root cause analysis, fix identification, and iterative re-verification.
---

# FPGA Module Debugging Workflow

Base directory for this skill: the repository root (where `run.py` lives).

This skill guides debugging of failing FPGA simulation tests. It uses an iterative **diagnose-fix-verify** loop that integrates with the development phases from `fpga-module-dev`.

## Debugging Principles

### 1. Never guess — diagnose first

Do not jump to code changes. Every fix must be preceded by a root cause analysis that identifies **what is wrong** and **why**. A wrong diagnosis leads to wrong fixes that mask the real problem or introduce new ones.

### 2. Investigation priority order

When a simulation fails, investigate in this order:

1. **Behavioral sim models** — delta-cycle races, incorrect timing, missing delays in FPGA primitive wrappers
2. **BFM/VVC configuration** — timeouts, clock frequencies, protocol settings (e.g. `max_wait_cycles` too short)
3. **Test harness wiring** — signal connections, type mismatches, undriven signals, wrong generics
4. **Testbench logic** — incorrect stimulus sequencing, wrong expected values, missing waits
5. **RTL bugs** — investigate the DUT, e.g. FSM logic, data path, control signals

### 3. Fix at the right phase

Every fix maps back to a development phase from `fpga-module-dev`. Identify the root cause category, then update from that phase forward:

| Root Cause | Fix Phase | Update Through |
|---|---|---|
| Wrong/missing requirement | A (Specification) | A -> B -> C -> D -> E -> F |
| Architectural flaw (FSM logic, data path) | B (Architecture) | B -> C -> D -> E -> F |
| Missing test coverage | C (Verification Plan) | C -> E -> F |
| RTL implementation bug | D (RTL) | D -> E -> F |
| Testbench/harness bug | E (Testbench) | E -> F |
| Sim model / BFM config issue | E (Testbench) | E -> F |

Do **not** fix RTL to work around a testbench bug. Do **not** fix a testbench to hide an architectural flaw.

---

## The Diagnose-Fix-Verify Loop

```
    +---------------------------+
    |  1. RUN FAILING TEST      |
    |     Capture UVVM log      |
    +------------+--------------+
                 |
                 v
    +---------------------------+
    |  2. ANALYZE UVVM LOG      |
    |     Identify failure point |
    |     Extract error context  |
    +------------+--------------+
                 |
        Is the root cause clear?
        |                  |
       YES                 NO
        |                  |
        |                  v
        |   +---------------------------+
        |   |  3. WAVEFORM ANALYSIS     |
        |   |     Re-run with --log-waves|
        |   |     Query signals at       |
        |   |     failure time           |
        |   |     Trace data flow        |
        |   +------------+--------------+
        |                |
        v                v
    +---------------------------+
    |  4. READ SOURCE CODE      |
    |     Examine RTL / TB at   |
    |     the identified location|
    |     Confirm root cause     |
    +------------+--------------+
                 |
                 v
    +---------------------------+
    |  5. IDENTIFY FIX PHASE    |
    |     Map root cause to      |
    |     development phase      |
    +------------+--------------+
                 |
                 v
    +---------------------------+
    |  6. APPLY FIX             |
    |     Update docs if needed  |
    |     Modify code            |
    +------------+--------------+
                 |
                 v
    +---------------------------+
    |  7. RE-RUN TEST           |
    |     Verify fix             |
    +------------+--------------+
                 |
            Pass?
           /     \
         YES      NO --> back to step 2
          |
          v
    +---------------------------+
    |  8. RUN FULL MODULE TESTS |
    |     Ensure no regressions  |
    +---------------------------+
```

---

## Step-by-Step Instructions

### Step 1: Run the Failing Test

Run the specific failing test verbosely to capture the full UVVM log output:

```bash
python run.py -v "*<module>*<test_name>*"
```

Capture the output. Pay attention to:
- The **UVVM alert summary** at the end (which alerts were raised, their severity)
- The **simulation time** when the first error occurred
- The **check_value** or **await_value** failure messages (they contain expected vs. actual values)
- Any **timeout** messages (often indicates a missing event or wrong timing)

### Step 2: Analyze the UVVM Log

Read the test output carefully. UVVM provides structured error messages:

```
FAILURE: check_value => Got 0x00, Expected 0xFF. [source: <file>:<line>]
```

Extract:
- **What failed:** Which check, which signal, which VVC
- **When it failed:** Simulation time of the error
- **Expected vs. actual:** The mismatch values
- **Where in the testbench:** The source location of the failing check

If the log clearly identifies the root cause (e.g., a wrong expected value in the testbench, a timeout indicating a missing clock), proceed to Step 4.

If the log is ambiguous (e.g., data corruption, unexpected state, timing issue), proceed to Step 3 for waveform analysis.

#### Common UVVM Error Patterns

| Log Pattern | Meaning | Typical Cause |
|---|---|---|
| `check_value => Got X, Expected Y` | Value mismatch at a specific check | RTL bug (wrong output) or testbench bug (wrong expected value) |
| `await_value => Timeout` | Signal never reached expected value within `max_wait_cycles` | Missing stimulus, deadlocked handshake, or `max_wait_cycles` too short |
| `await_completion => Timeout` | VVC command did not complete | BFM config timeout too short, or DUT never responded to transaction |
| Alert summary with non-zero ERROR/FAILURE | End-of-sim alert counts | Check counts — non-zero ERROR or above means test failed |

**BFM timeout false positives:** If the only failure is an `await_value` or `await_completion` timeout and the DUT logic appears correct in waveforms, the BFM `max_wait_cycles` is likely too short. Fix the VVC config, not the DUT. See `fpga-module-dev` Phase E §VVC/BFM Timeout Configuration.

**UVVM alert severity levels** (ascending): `NOTE < TB_NOTE < WARNING < TB_WARNING < ERROR < TB_ERROR < FAILURE < TB_FAILURE`. `TB_*` variants are for testbench-internal alerts. `ERROR` and above cause test failure by default.

### Step 3: Waveform Analysis with `wavequery`

The `wavequery` tool is located at `.claude/skills/fpga-module-dbg/wavequery.py`.

#### 3a. Re-run with waveform capture

```bash
python run.py --log-waves -v "*<module>*<test_name>*"
```

The `--log-waves` flag records all signals to the WLF file. This slows simulation, so use it only for the specific failing test.

#### 3b. Discover available signals

```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" list-signals --filter "*dut*"
```

Use `--filter` to narrow down to the DUT hierarchy, a specific sub-block, or interface signals.

#### 3c. Query signals at the failure time

Use the failure time from the UVVM log. Common queries:

**Check signal value at a specific time:**
```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" value-at \
    --signal "*<signal_name>*" --time <failure_time>
```

**Trace all transitions of a signal around the failure:**
```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" transitions \
    --signal "*<signal_name>*" --from <before_failure> --to <after_failure>
```

**Check FSM state at the failure time:**
```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" fsm \
    --signal "*state*" --names "IDLE=00,READY=01,BUSY=10,DONE=11"
```

**Find when a signal transitioned (e.g., reset deassertion):**
```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" find-edge \
    --signal "*rst_n*" --edge rising --nth 1
```

**Measure how long a signal holds a value:**
```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" duration \
    --signal "*state*" --value "0010" --after 0ns
```

**Compare expected vs. actual at multiple time points:**
```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" compare \
    --signal "*data_out*" --expect "1us=00FF,2us=0A0B,3us=DEAD"
```

#### 3d. Recommended investigation sequence

For a typical data-path failure:

1. **Check the FSM state** at the failure time — is the DUT in the expected state?
2. **Check input signals** — was the stimulus correct? Were handshake signals (valid/ready) asserted?
3. **Check output signals** — what did the DUT actually produce?
4. **Trace backward** — find when the signal diverged from expected. Use `transitions` with a time range ending at the failure.
5. **Check control signals** — clock enables, mux selects, counter values at the divergence point.

For a timeout failure:

1. **Check the signal being waited on** — did it ever transition?
2. **Check upstream signals** — is the DUT receiving the input that would trigger the waited event?
3. **Check handshakes** — is backpressure blocking the pipeline?
4. **Check reset** — did reset deassert when expected?

#### 3e. Use JSON output for programmatic analysis

Add `--format json` for structured output that is easier to process:

```bash
python .claude/skills/fpga-module-dbg/wavequery.py --test "*<test>*" --format json \
    transitions --signal "*state*"
```

### Step 4: Read the Source Code

Once you have a hypothesis from the log/waveform analysis, **read the relevant source code** to confirm the root cause:

- **For RTL bugs:** Read the VHDL source in `hdl/<module>/src/` at the logic that produces the wrong signal. Trace the combinational/sequential path from inputs to the failing output. Check state machine transitions, pipeline stages, and data formatting.
- **For testbench bugs:** Read the test harness (`_th.vhd`) for wiring errors and the testbench (`_tb.vhd`) for stimulus/check errors. Verify VVC configurations, timeout settings, and expected data construction.
- **For sim model bugs:** Read `tb/sim_models/` for behavioral models of FPGA primitives. Check delta-cycle ordering (see fpga-module-dev guidance on VHDL/Verilog mixed simulation).
- **For architectural issues:** Read the architecture doc (`docs/architecture.md`) and compare against the RTL. Check if the state machine, data path, or interface behaviour matches the specification.

### Step 5: Identify the Fix Phase

Based on the confirmed root cause, determine which development phase the fix belongs to:

- **Specification error** (requirement is wrong or missing) -> Phase A
- **Architecture error** (FSM has wrong transitions, pipeline is wrong) -> Phase B
- **Missing test case** (this scenario wasn't covered) -> Phase C
- **RTL bug** (code doesn't match architecture) -> Phase D
- **Testbench bug** (wrong stimulus, wrong expected values, wrong VVC config) -> Phase E
- **Sim model issue** (behavioral model doesn't match real hardware) -> Phase E

### Step 6: Apply the Fix

Apply the fix at the identified phase. If the fix is at Phase D or earlier, update all downstream phases:

- **Phase D fix (RTL):** Modify the source, then verify the testbench still makes sense for the changed behaviour.
- **Phase E fix (testbench):** Modify the test harness or testbench. No upstream changes needed.
- **Phase B fix (architecture):** Update the architecture doc first, then update verification plan, RTL, and testbench.

### Step 7: Re-run the Failing Test

```bash
python run.py -v "*<module>*<test_name>*"
```

If the test **passes**, proceed to Step 8.

If the test **still fails**, return to Step 2. Re-analyze the log — the failure mode may have changed, revealing a secondary issue or indicating the fix was incomplete.

### Step 8: Run Full Module Tests

After the specific test passes, run all tests for the module to check for regressions:

```bash
python run.py -v "*<module>*"
```

All tests must pass before the fix is considered complete.

---

## Wavequery Tool Reference

**Location:** `.claude/skills/fpga-module-dbg/wavequery.py`

**Prerequisites:** `pip install vcdvcd`

### Global Options

| Option | Description |
|---|---|
| `--test PATTERN` | Test name glob pattern (e.g. `*boot*fail*`) |
| `--vcd PATH` | Direct path to a VCD file |
| `--wlf PATH` | Direct path to a WLF file (auto-converts to VCD) |
| `--format {table,json}` | Output format (default: table) |
| `--vunit-out PATH` | Override VUnit output directory |

### Subcommands

| Command | Purpose |
|---|---|
| `list-tests` | List tests with available WLF/VCD files |
| `list-signals` | List all signals in a waveform (with `--filter` glob) |
| `value-at` | Get signal value(s) at specific time(s) |
| `transitions` | List all transitions in a time range (`--from`, `--to`) |
| `find-edge` | Find the Nth rising/falling edge of a signal |
| `duration` | Measure how long a signal holds a specific value |
| `compare` | Compare expected vs. actual values at given times |
| `fsm` | Trace state machine transitions with named states |

### Time Formats

All time arguments accept: `100ps`, `200ns`, `1.5us`, `10ms`, `0.5s`. Plain integers are treated as picoseconds.

### Signal Patterns

Signal names use glob matching (case-insensitive). Use `*` to match any part of the hierarchy:
- `*dut*state*` — any signal containing "dut" and "state"
- `*i_th/i_dut/state*` — specific hierarchy path
- `*axi*tvalid*` — any AXI tvalid signal

If a pattern matches multiple signals, the tool reports all matches and asks you to be more specific.

---

## Common Debugging Scenarios

### Scenario: AXI-Stream data mismatch

1. UVVM reports `axistream_expect` failure with wrong data byte
2. Re-run with `--log-waves`
3. Use `transitions` on the AXI-Stream `tdata` signal around the failure time
4. Compare with the expected data construction in the testbench
5. If DUT output is wrong: trace the data path backward through the DUT using `value-at` on intermediate signals
6. If expected data is wrong: fix the testbench (Phase E)

### Scenario: Timeout waiting for event

1. UVVM reports `await_value` timeout
2. Re-run with `--log-waves`
3. Use `value-at` to check if the awaited signal ever reached the expected value
4. Use `transitions` on the awaited signal to see its full history
5. Trace upstream: what input was the DUT waiting for? Use `value-at` on DUT inputs at the timeout time
6. Common causes: VVC `max_wait_cycles` too short (fix BFM config), missing stimulus (fix testbench), deadlocked handshake (fix RTL)

### Scenario: FSM stuck in wrong state

1. Test fails because DUT never transitions to expected state
2. Re-run with `--log-waves`
3. Use `fsm` to trace all state transitions with named states
4. Identify where the FSM diverged from expected behaviour
5. Use `value-at` to check the transition conditions at the divergence point
6. Read the RTL state machine code and compare against the architecture doc

### Scenario: Reset timing issue

1. Signals have unexpected values immediately after reset
2. Use `find-edge` on `rst_n` to find reset deassertion time
3. Use `value-at` on DUT outputs just after reset deassertion
4. Check if the DUT needs additional clock cycles after reset before it's ready
5. Common cause: testbench starts stimulus too early after reset (fix Phase E wait time)

### Scenario: Clock domain crossing issue

1. Symptoms: intermittent test failures, data corruption that appears/disappears between runs, signals that "glitch" to wrong values for a single cycle
2. Suspect CDC if the failing signal crosses between two different clocks — check the test harness and architecture doc for clock domain boundaries
3. Re-run with `--log-waves`; use `transitions` to look for single-cycle glitches or data values that change incoherently (multiple bits changing at different times)
4. Verify the synchronizer type matches the signal type:
   - Single bit -> `olo_base_cc_bits`
   - Pulse -> `olo_base_cc_pulse`
   - Multi-bit vector -> `olo_base_cc_simple`, `olo_base_cc_handshake`, or `olo_base_fifo_async`
   - Continuous stream -> `olo_base_fifo_async`
5. Common fixes: add missing synchronizer, replace 2-FF synchronizer on a bus with an async FIFO, ensure FIFO read/write clocks are correctly connected
6. After fixing, run multiple times — CDC bugs may pass once by luck

### Scenario: AXI-Lite register read/write failure

1. UVVM reports wrong data on an AXI-Lite read, or a write has no observable effect
2. For **wrong read data:**
   - Check address decoding logic — is the address offset correct and properly aligned?
   - Check register reset values — does the register initialize to the expected default?
   - Check read-clear (RC) fields — reading a register with RC bits clears them; a second read returns zero
   - Use `value-at` on the register signal inside the DUT at the read time to confirm the stored value
3. For **write has no effect:**
   - Check the address mapping matches the testbench's target address
   - Check the register access type — writing to a read-only (RO) field is silently ignored
   - Check bit-field masks — a write to a 4-bit field in a 32-bit register must not corrupt adjacent fields
4. Use `transitions` on the register signal to see if/when the value changed
5. Cross-reference the register map in the architecture doc (`docs/architecture.md` §Register Map)
