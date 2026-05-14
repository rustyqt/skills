---
name: fpga-module-dev
description: Guides FPGA module development through a mandatory six-phase workflow covering requirements, architecture, design description, verification planning, RTL implementation, and testbench implementation using VUnit and UVVM. Use when the user asks to create, develop, design, verify, or test an FPGA module, IP core, or VHDL component in this repository.
---

# FPGA Module Development Workflow

Every FPGA module development follows a **mandatory six-phase** development process. Do not skip or reorder phases. Each phase must be reviewed/approved before proceeding to the next.

## Phase Overview

```
A) Specify requirements              → hdl/<module>/docs/specification.md
B) Architecture & design description → hdl/<module>/docs/architecture.md
C) Write verification plan           → hdl/<module>/docs/verification_plan.md
D) Implement RTL                     → hdl/<module>/src/*.vhd
E) Implement testbenches             → hdl/<module>/tb/*_tb.vhd, *_th.vhd
F) Verification                      → run VUnit tests + regression; output: hdl/<module>/docs/verification_report.md
```

Track progress with a checklist:

```
Module: <module_name>
- [ ] Phase A: Requirements specified
- [ ] Phase B: Architecture & design description created
- [ ] Phase C: Verification plan written
- [ ] Phase D: RTL implemented
- [ ] Phase E: Testbenches implemented
- [ ] Phase F: Verification complete (all tests passing, regression run, report written)
```

## Mapping to ECSS-E-ST-20-40C Development Flow

This module-level workflow covers the ECSS development phases up to and including the **DEVICE Design and Verification Phase**:

| ECSS Phase | Module Workflow Phase | Key Outputs |
|------------|----------------------|-------------|
| **DEVICE Definition Phase** | **A) Specify requirements** | Module specification derived from FPGA-level requirements (DRS equivalent at module level) |
| **DEVICE Architecture Definition Phase** | **B) Architecture & design description** | Block diagram, port maps, state machines, data formats (Architecture Definition Report equivalent) |
| **DEVICE Design and Verification Phase** | **C) Verification plan** | Test cases with requirement traceability (DVeP equivalent at module level) |
| **DEVICE Design and Verification Phase** | **D) RTL implementation** | Synthesizable VHDL (simulation models for DEVICE Database) |
| **DEVICE Design and Verification Phase** | **E) Testbench implementation** | VUnit+UVVM testbenches (Design Verification Report inputs) |
| **DEVICE Design and Verification Phase** | **F) Verification** | Test execution, regression, results & requirement coverage (Design Verification Report equivalent) |

Subsequent ECSS phases (Detailed Design, Layout, Implementation, Validation) operate at the full FPGA level and are outside the scope of this module-level workflow.

---

## Design Library: Open Logic

**Open Logic** (`open-logic/`, included as a **git submodule**) is the preferred VHDL design library. Always check it first before writing standard building blocks: FIFOs, clock-domain crossings, RAMs, arbiters, pipeline stages, width converters, CRC, I2C/SPI/UART, fixed-point math.

Browse `open-logic/doc/EntityList.md` for the entity list. Compile required sources into a single VHDL library (e.g. `olo`); see `open-logic/compile_order.txt`. The `base` area has no external dependencies; `axi` and `intf` depend on `base`; `fix` depends on `base` plus `en_cl_fix` (`open-logic/3rdParty/en_cl_fix`).

If an entity covers the requirement, instantiate it directly — do not duplicate its logic. If extra behaviour is needed, wrap the entity and add only the delta around it.

---

## Verification Framework: UVVM

**UVVM** (`uvvm/`, included as a **git submodule**) provides all testbench infrastructure used in Phase E: VVCs (e.g. `axistream_vvc`), BFMs, alert/log handling, awaiters (`await_value`, `await_uvvm_initialization`), checkers (`check_value`), constrained randomization (`t_rand`), and functional coverage (`func_cov_pkg`). VUnit drives test discovery and execution; UVVM supplies the verification building blocks. No other randomization or coverage framework is used.

---

## Repository Top-Level Structure

The repository follows this **mandatory top-level layout**:

```
<repo_root>/
├── constraints/        # Top-level constraints (placement .pdc, timing .sdc)
├── docs/               # Top-level documentation (FPGA-level requirements spec, system architecture)
├── hdl/                # Self-developed FPGA modules (produced by this skill)
│   └── <module_name>/  # Per-module folder — see "Module Directory Structure" below
├── open-logic/         # Git submodule — Open Logic design library
├── uvvm/               # Git submodule — UVVM verification framework
├── tcl/                # Tool scripts (e.g. FPGA vendor toolchain build scripts)
└── run.py              # VUnit test runner
```

---

## Module Directory Structure

Create this layout for every new module:

```
<module_name>/
├── README.md                      # Brief overview and testbench usage instructions
├── src/
│   ├── <module_name>.vhd          # Top-level synthesizable entity (phase D)
│   └── <module_name>_pkg.vhd      # Optional support package (phase D)
├── tb/
│   ├── <module_name>_tb.vhd       # VUnit testbench (phase E)
│   └── <module_name>_th.vhd       # UVVM test harness (phase E)
├── docs/
│   ├── specification.md           # Requirements (phase A)
│   ├── architecture.md            # Architecture and design description (phase B)
│   ├── verification_plan.md       # Verification plan with requirement traceability (phase C)
│   └── verification_report.md     # Test execution results (phase F)
└── script/
    └── compile_order.txt          # Optional compile order overrides
```

The `README.md` shall only contain:
- A one-paragraph module description
- A table linking to the docs (specification, architecture, verification plan, verification report)
- Testbench prerequisites and how to run tests
- Testbench file descriptions

Add the module name to `component_list.txt` at the repository root, respecting dependency order.

---

## Phase A: Specify Requirements

Create `<module>/docs/specification.md`.

### Requirement Sources

Requirements come from two sources:

1. **FPGA-level requirements** — taken from the FPGA-level specification in `<project_dir>/docs/spec/`. These are flowed down verbatim using the **exact requirement ID and text** from the FPGA-level spec. They establish the traceable link between module and system.

2. **Module-level requirements** — derived from user input, engineering reasoning, or further decomposition of the FPGA-level spec. These use the format **`<MODULE_NAME>-<XXX>`** where `<MODULE_NAME>` is the module name in uppercase and `XXX` is a three-digit number (e.g. `MY_FIFO-001`, `MY_CTRL-012`).

### Requirement Format

Each requirement must have:
- A unique ID (FPGA-level ID for flowed-down requirements, `<MODULE_NAME>-<XXX>` for module-level)
- A concise "shall" statement
- Grouped by category (interface, functional, error handling, etc.)

Use this structure:

```markdown
# <Module Name> Specification

## 1. Overview
- Purpose and key features

## 2. Requirements

### 2.1 Interface Requirements
- **<MODULE_NAME>-001:** Module shall provide an AXI4-Stream slave interface for data ingestion *(flowed down from FPGA spec)*
- **<MODULE_NAME>-002:** Module shall provide an AXI4-Lite slave interface for configuration *(flowed down from FPGA spec)*

### 2.2 Functional Requirements
- **<MODULE_NAME>-003:** Module shall process input data within N clock cycles *(flowed down from FPGA spec)*
- **<MODULE_NAME>-004:** Module shall assert output valid when processing completes *(module-level)*

### 2.3 Error Handling
- **<MODULE_NAME>-005:** Module shall detect and flag invalid input conditions *(module-level)*
- **<MODULE_NAME>-006:** Module shall recover to idle state after errors *(module-level)*

## 3. Error Conditions
(table of error conditions, detection, and response)

## 4. Configuration Parameters
(table of generics with defaults and ranges)
```

All requirements MUST be traceable forward into the verification plan (phase C).

---

## Phase B: Architecture & Design Description

Create `<module>/docs/architecture.md` as a complete design document covering both the architectural overview and the detailed design description.

Required contents:
- Block diagram (ASCII art)
- Sub-block decomposition (state machines, datapaths, control logic)
- Interface definitions (port list with signal names, widths, directions)
- Internal data flow and pipeline stages
- Configuration parameters (generics) with defaults and valid ranges
- Detailed register map (address, name, access, bit fields) — if applicable
- State machine descriptions (ASCII art diagrams)
- Data format diagrams (packet structures, memory layouts)
- Timing diagrams or behavioural descriptions for key operations
- Error conditions and recovery behaviour

Use tables for port/register maps. Example:

```markdown
# <Module Name> Architecture & Design Description

## 1. Block Diagram
(ASCII art)

## 2. Sub-Block Descriptions
...

## 3. Top-Level Ports
| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| clk    | 1     | Input     | System clock |
| rst_n  | 1     | Input     | Active-low reset |

Preferred interfaces are AXI-Stream for streaming data and AXI-Lite for control signals (use olo_axi_lite_slave). Their signals should follow the standard naming conventions (e.g. `s_axis_*`, `m_axis_*` for AXI-Stream).

## 4. Configuration Parameters
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| DATA_WIDTH | 16 | 8-64 | Data bus width |

## 5. State Machine Descriptions
(ASCII art state diagrams, transition tables)

## 6. Data Formats
(packet structures, memory layouts)

## 7. Register Map
(address, name, access type, bit field descriptions)

## 8. Timing & Behaviour
(timing diagrams or behavioural descriptions for key operations)
```

Use the highest-quality existing module in the repository as the reference example.

---

## Phase C: Write Verification Plan

Create `<module>/docs/verification_plan.md`. Every test case must trace back to requirements from phase A.

### Verification Plan Structure

```markdown
# <Module Name> Verification Plan

**Module:** <module_name>
**Date:** <date>

## 1. Overview
- Verification objectives (bulleted list)
- Test environment (testbench file, simulator, interfaces)

## 2. Test Configuration
- Test constants and parameters (table)
- Data structures under test (ASCII diagrams)

## 3. Test Case Documentation

### 3.N Test Case N: <Descriptive Name>

**Test ID:** `test_<snake_case_name>`
**Objective:** <one-line objective>

#### Requirements Covered
| Req ID | Requirement | Verification Method |
|--------|-------------|---------------------|
| <MODULE_NAME>-001 | <shall statement> | <how it is verified> |

#### Test Sequence
1. **Setup** — configure DUT
2. **Stimulus** — drive inputs
3. **Verify** — check outputs/registers

#### Pass Criteria
- ✅ <criterion 1>
- ✅ <criterion 2>

## 4. Coverage Analysis
- Functional coverage table
- Requirement traceability matrix

## 5. Functional Coverage Plan
| Coverpoint | Requirement(s) | Bins | Goal |
|------------|----------------|------|------|
| <COVPT_NAME> | <MODULE_NAME>-001 | min, nominal[N], max, illegal | 90% |
```

The verification plan does NOT contain test results. Results go in phase F (verification report).

Every requirement from phase A must appear in at least one test case's "Requirements Covered" table. Verify full traceability before proceeding.

### Functional Coverage Planning

For each functional requirement that defines a range or set of valid inputs/outputs, define a **coverpoint** with bins that partition the input space:

- **Boundary bins:** Minimum and maximum valid values (e.g., `bin(1)`, `bin(1024)`)
- **Nominal bins:** Middle-range values split into sub-ranges (e.g., `bin_range(2, 1023, 4)`)
- **Illegal bins:** Values outside the valid range (e.g., `illegal_bin_range(1025, 65535)`)


---

## Phase D: Implement RTL

Write synthesizable VHDL in `<module>/src/`. Follow these conventions:

- **Language:** VHDL-2008
- **Entity naming:** matches the module folder name (e.g. `axis_fifo/src/axis_fifo.vhd`)
- **Architecture naming:** `rtl` for synthesizable code
- **Reset:** active-low asynchronous or synchronous (match project convention, prefer `rst_n`)
- **Clock:** single clock domain, named `clk`
- **Generics:** provide sensible defaults; document valid ranges
- **Signals:** use `_i` / `_o` suffixes or AXI-Stream naming (`s_axis_*`, `m_axis_*`)
- **Reuse Open Logic blocks:** Before writing any standard building block (FIFO, clock crossing, width converter, pipeline stage, RAM, arbiter, CRC, etc.), check the Open Logic entity list (`open-logic/doc/EntityList.md`). Instantiate the proven Open Logic entity instead of reimplementing equivalent logic.
- **External signal synchronization:** Treat all signals originating from outside the FPGA (I/O pins, off-chip devices) as asynchronous to the system clock by default. Synchronize them using `olo_base_cc_bits` (one instance per independent signal group) before any internal logic samples them. Connect both `In_Clk` and `Out_Clk` to the module's system clock when no source clock exists. Internal FPGA-to-FPGA signals between modules sharing the same clock domain do not require synchronization.
- **Synchronous design rules**:
  - Use only edge-triggered flip-flops — never infer a latch. Every `if` in a clocked process must have an `else`; every `case` must have `when others`. If synthesis warns about a latch, treat it as a bug.
  - No combinational feedback loops — every feedback path must pass through a register.
  - No gated clocks — use clock enables (`if clk_en = '1' then`) instead of gating the clock signal.
  - Clock all flip-flops on the same edge (rising).
  - Provide a reset value for every register in the reset branch of the clocked process.

### Clock Domain Crossing (CDC)

Any signal crossing between two different clock domains requires explicit synchronization. Choose the Open Logic CDC entity that matches the signal type:

| Signal Type | Open Logic Entity | Use When |
|---|---|---|
| Single-bit level(s) | `olo_base_cc_bits` | Status flags, enables, control bits |
| Single-cycle pulse | `olo_base_cc_pulse` | Interrupt pulses, trigger events |
| Multi-bit vector (slow updates) | `olo_base_cc_simple` or `olo_base_cc_status` | Configuration registers, slow-changing status |
| Multi-bit vector (handshake) | `olo_base_cc_handshake` | Single transfers with backpressure |
| Continuous data stream | `olo_base_fifo_async` | Streaming data between clock domains |
| Reset | `olo_base_cc_reset` | Synchronizing reset release across domains |

Rules:
- Never pass an unsynchronized signal across a clock domain boundary.
- Never use a 2-FF synchronizer on a multi-bit bus (bits may arrive in different cycles). Use an async FIFO or handshake mechanism.
- If in doubt, use `olo_base_fifo_async` — it is the safest general-purpose CDC mechanism.


### Retiming

For data pipeline modules where timing closure is critical, enable retiming at the **module level** using the `syn_allow_retiming` synthesis attribute. This allows the synthesis tool to move registers across combinational logic to balance path delays:

```vhdl
architecture rtl of data_pipeline is
    attribute syn_allow_retiming : boolean;
    attribute syn_allow_retiming of rtl : architecture is true;
begin
    ...
end architecture;
```

Note: Only enable retiming if dedicated pipeline stages are not sufficient to meet timing.

### Style Linting

Run VHDL Style Guide on all RTL files after implementation:
```bash
vsg -c .vscode/vsg.yaml -f <file> --fix
```
Fix all violations before proceeding to Phase E.

The implementation must satisfy every requirement from phase A and conform to the architecture from phase B.

---

## Phase E: Implement Testbenches

Create two files per testable entity:

### Test Harness (`<module>_th.vhd`)

Provides infrastructure only — no test logic.

Required contents:
1. Instantiate `uvvm_vvc_framework.ti_uvvm_engine`
2. Generate clock and reset
3. Instantiate the DUT
4. Instantiate UVVM VVCs or BFMs as needed
5. Wire everything together

Template (adapt widths/VVCs to the module):

```vhdl
library ieee;
use ieee.std_logic_1164.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library uvvm_vvc_framework;
use uvvm_vvc_framework.ti_vvc_framework_support_pkg.all;

entity <module>_th is
end entity;

architecture th of <module>_th is
  constant C_CLK_PERIOD : time := 10 ns;
  signal clk   : std_logic := '0';
  signal rst_n : std_logic := '0';
  -- DUT signals here
begin
  i_ti_uvvm_engine : entity uvvm_vvc_framework.ti_uvvm_engine;

  p_clk : process
  begin
    clk <= '0'; wait for C_CLK_PERIOD/2;
    clk <= '1'; wait for C_CLK_PERIOD/2;
  end process;

  p_reset : process
  begin
    rst_n <= '0'; wait for 100 ns;
    rst_n <= '1'; wait;
  end process;

  -- DUT instantiation
  -- VVC instantiations (if applicable)
end architecture;
```

### Testbench (`<module>_tb.vhd`)

Contains test logic. Must use both VUnit and UVVM patterns:

```vhdl
library ieee;
use ieee.std_logic_1164.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library uvvm_vvc_framework;
use uvvm_vvc_framework.ti_vvc_framework_support_pkg.all;

library vunit_lib;
context vunit_lib.vunit_context;

entity <module>_tb is
  generic (runner_cfg : string);
end entity;

architecture tb of <module>_tb is
begin
  p_main : process
  begin
    await_uvvm_initialization(VOID);
    test_runner_setup(runner, runner_cfg);
    wait for 200 ns; -- allow reset to deassert

    if run("test_case_name") then
      -- Test stimulus and checks here
    end if;

    -- More test cases ...

    test_runner_cleanup(runner);
    wait;
  end process;

  i_th : entity work.<module>_th;
end architecture;
```

Key rules:
- Test case names in `run("...")` must match the Test IDs from the verification plan
- One `if run(...) then ... end if;` block per test case
- Use UVVM `check_value()`, `await_value()` for assertions alongside VUnit's test runner
- Use UVVM VVCs (e.g. `axistream_transmit`, `axistream_expect`) when available for the interface type
- Call `await_uvvm_initialization(VOID)` before any UVVM operation
- Using the UVVM set_alert_stop_limit procedure is forbidden. 

### Behavioral Simulation Models for FPGA Primitives

When writing VHDL behavioral models for FPGA-specific primitives (DDR output buffers, I/O pads, clock buffers, etc.) that interface with **Verilog IP** in mixed-language simulation, respect the delta-cycle ordering between VHDL and Verilog:

- **Problem:** If a VHDL process triggers on the same clock edge as a Verilog module, the VHDL process may read output ports of the Verilog module **before** non-blocking assignments have settled. This produces stale values and glitches that corrupt downstream logic.
- **Fix:** Add a small real-time delay (e.g., `wait for 100 ps;`) before sampling signals driven by Verilog modules. This guarantees all Verilog NBA updates have propagated. Example:

- Place custom behavioral sim models in `<module>/tb/sim_models/` and compile them into the library that contains the instantiating entity, so default component binding resolves correctly.
- Vendor-supplied Verilog primitive models (e.g. I/O buffers, clock buffers, register primitives) generally work correctly in mixed-language simulation with QuestaSim when compiled into a dedicated library and referenced via `-L <lib>`.

### VVC/BFM Timeout Configuration

Default UVVM VVC timeout values (`max_wait_cycles`) are often too short for interfaces with inherent latency (link initialization sequences, multi-cycle memory operations, etc.). Always configure timeouts based on the actual interface timing:

```vhdl
-- Example: an interface needs ~25 us to initialize.
-- At 50 MHz sys_clk, 25 us = 1250 cycles — far exceeds the default 100 cycles.
shared_axistream_vvc_config(C_VVC_TX).bfm_config.max_wait_cycles := 10000;
shared_axistream_vvc_config(C_VVC_RX).bfm_config.max_wait_cycles := 10000;
```

Similarly, increase the VUnit watchdog timeout to accommodate long initialization sequences.

### Debugging Principle: Test Infrastructure First

When a simulation fails, investigate in this order:

1. **Behavioral sim models** — delta-cycle races, incorrect timing, missing delays
2. **BFM/VVC configuration** — timeouts, clock frequencies, protocol settings
3. **Test harness wiring** — signal connections, type mismatches, undriven signals
4. **DUT bugs** — only after ruling out test infrastructure issues

Only fix the DUT for genuine RTL bugs. Simulation-only problems (e.g., FPGA primitive models not matching Verilog timing semantics) belong in the test infrastructure (`tb/sim_models/`, test harness, BFM config).

### Data Verification Principles

Always verify received data against expected values rather than only confirming arrival:

- **Prefer `axistream_expect` over `axistream_receive`:** `axistream_expect` compares actual data against an expected pattern byte-by-byte, catching data corruption, wrong header reconstruction, and protocol errors that `axistream_receive` would silently accept.
- When the DUT transforms data (e.g. replaces headers, inserts timestamps, modifies sequence counters), build the expected output packet separately using the known DUT configuration and use it as the reference for `axistream_expect`.
- For packets that do not fill the last AXI-Stream beat completely, use a flat `std_logic_vector` of exactly `nbytes*8` bits rather than a beat-oriented array. This avoids sideband and padding-byte comparison issues with UVVM.
- Use `LOWER_BYTE_RIGHT` byte endianness consistently for the AXI-Stream VVCs and the expected data construction.

### Mandatory Stress Tests for AXI-Stream Interfaces

Every module with AXI-Stream interfaces **must** include the following stress test categories in its verification plan:

1. **Random backpressure:** Configure the UVVM AXI-Stream slave VVC with randomized `tready` deassertions to verify the DUT handles backpressure correctly. Use the UVVM BFM config fields:
   ```vhdl
   shared_axistream_vvc_config(N).bfm_config.ready_low_duration             := C_RANDOM;
   shared_axistream_vvc_config(N).bfm_config.ready_low_max_random_duration  := 4;
   shared_axistream_vvc_config(N).bfm_config.ready_low_at_word_num          := C_MULTIPLE_RANDOM;
   shared_axistream_vvc_config(N).bfm_config.ready_low_multiple_random_prob := 0.30;
   ```
   The DUT must produce identical output data regardless of backpressure patterns.

2. **Back-to-back transfers:** Send multiple packets without idle cycles between them to verify the DUT can sustain line-rate throughput and correctly frames consecutive packets.

3. **Throughput measurement:** For data-path modules, measure actual throughput in simulation (bytes transferred / simulation time) and assert it meets the design target for the given clock frequency and data width.

4. **Simultaneous RX/TX:** For modules with independent RX and TX paths, run both concurrently to verify no cross-path interference.

### Constrained Random Verification

In addition to directed test cases, add constrained random tests to discover corner cases. Use UVVM's `t_rand` type for randomization (supports basic randomization, weighted distributions, and range exclusions):

```vhdl
variable v_rand : t_rand;
v_rand.set_rand_seeds(v_rand'instance_name);  -- Deterministic seed for CI reproducibility
v_rand.add_val_weight(0, 5);      -- Bias towards boundary values
v_rand.add_val_weight(255, 5);
v_rand.add_range(1, 254);
v_data := v_rand.randm(VOID);
```

Each requirement must still have a directed test case for traceability. Random tests supplement directed tests with broader input coverage.

### Functional Coverage

Use UVVM's `func_cov_pkg` to measure which design scenarios the tests actually exercised. Define coverpoints matching the functional coverage plan from Phase C:

```vhdl
shared variable shared_covpt : t_coverpoint;

-- Configure bins (in test case)
shared_covpt.set_name("PKT_SIZE");
shared_covpt.set_bins_coverage_goal(90);
shared_covpt.add_bins(bin(1), 5, "min");
shared_covpt.add_bins(bin_range(2, 1023, 4), "nominal");
shared_covpt.add_bins(bin(1024), 5, "max");

-- Sample after each transaction
shared_covpt.sample_coverage(packet_size);

-- Run until covered (for random tests)
while not shared_covpt.coverage_completed(BINS) loop
    pkt_size := v_rand.rand(1, 1024);
    send_and_check(pkt_size);
    shared_covpt.sample_coverage(pkt_size);
end loop;

-- Report at end of test
shared_covpt.report_coverage(VERBOSE);
```

---

## Phase F: Verification

Phase F executes the testbenches written in Phase E, drives them to a passing regression, and documents the result. The phase has two parts: **(1) Run tests + regression** (the main task) and **(2) Write the verification report** (the output document).

### 1. Run Tests + Regression

The preferred simulator is **QuestaSim** (`VUNIT_SIMULATOR=modelsim`). Do not use GHDL.

FPGA-vendor simulation primitives (if required by the design) should be provided either by:
1. **Precompiled vendor library** from the vendor toolchain installation (preferred, auto-detected by `run.py` when available), or
2. **Fallback:** Verilog simulation models checked into the repo (e.g. under `hdl/libs/src/`).

These Verilog primitives work correctly in mixed-language (VHDL/Verilog) QuestaSim simulation via `-L <vendor_lib>` library search. If you write custom VHDL behavioral wrappers around Verilog IP or primitives, see "Behavioral Simulation Models for FPGA Primitives" in Phase E for delta-cycle ordering guidance.

```bash
python run.py --list              # discover tests
python run.py -v                  # run all tests verbosely (full regression)
python run.py -v "*<module>*"     # run only this module's tests
```

Iterate back to Phases D/E as needed until **every** test passes. A test that intermittently fails (e.g. due to randomization) must be fixed — not retried until it passes.

**Regression rule:** Every commit must pass the full regression — no exceptions. Run `python run.py -v` before every commit. A commit that breaks any test is not ready to merge.

### 2. Verification Report (Phase F Output)

Once all tests pass, create or update `<module>/docs/verification_report.md` with the actual results:

```markdown
# <Module Name> Verification Report

**Module:** <module_name>
**Date:** <date>

## 1. Test Results
| Test Case | Test ID | Status | Duration |
|-----------|---------|--------|----------|
| TC 1 | test_xxx | PASS | 1.2 ms |

## 2. Summary
(paste VUnit output from test execution)

## 3. Requirement Coverage
| Req ID | Requirement | Test Case(s) | Status |
|--------|-------------|--------------|--------|
| IF-001 | <shall statement> | TC 1, TC 3 | Covered |

## 4. Functional Coverage
| Coverpoint | Requirement(s) | Goal | Achieved | Uncovered Bins |
|------------|----------------|------|----------|----------------|
| PKT_SIZE | PKT-001 | 90% | 100% | — |

## 5. Overall Status
PASS / FAIL — <date>
```

The verification report is the final deliverable of the module workflow. It must be updated whenever tests are re-run. Every requirement from Phase A must appear in the coverage table.

---

## Reference Examples

To be established.

---

## Change Impact Assessment

When modifying an existing module, **do not jump to implementation**. Identify the earliest affected phase, then update every phase forward from there. Documentation is the specification of record — if code and docs disagree, the code is wrong.

| Change Type | Start At | Update Through |
|-------------|----------|---------------|
| New/modified requirement | A | A → B → C → D → E → F |
| Interface change (ports, widths, generics) | A | A → B → C → D → E → F |
| Architecture change (state machines, pipelines) | B | B → C → D → E → F |
| New test case only | C | C → E → F |
| Bug fix in RTL | D | D → E → F |
| Documentation-only correction | — | Affected doc only |

Before writing any RTL or testbench code, confirm all upstream docs (specification, architecture, verification plan) are already updated to reflect the change.
