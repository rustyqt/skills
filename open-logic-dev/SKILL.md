---
name: open-logic-dev
description: Guides the development of a new Open Logic entity through a mandatory six-phase workflow (proposal → entity declaration → RTL → testbench → documentation → integration & verification) with a user-review checkpoint at the end of every phase. Use when the user asks to create, develop, design, contribute, add, or implement a new VHDL entity, area, or module for the Open Logic library.
---

# Open Logic — New-Entity Development Workflow

This skill guides the development of a new entity for the **Open Logic** VHDL library
([open-logic/open-logic](https://github.com/open-logic/open-logic)). It is **the** workflow for adding any new
production entity to the repository. Do not skip or reorder the phases — Open Logic is contribution-driven and
every phase produces a deliverable that has to be reviewed before the next phase starts.

The official contribution rules and coding conventions are in:

- `Contributing.md` (repo root) — Larger Features procedure (Issue → fork → branch `feature/<name>` → PR to `develop`).
- `doc/Conventions.md` — entity / port / generic / signal / type naming rules. **Read this before writing any RTL.**
- `doc/HowTo.md` — using Open Logic with various tools (Questa, Vivado, Quartus, Libero, Efinity, Gowin, Yosys, FuseSoC).
- `doc/CI-Workflows.md` — what CI runs on every PR (HDL-Check on GHDL + NVC + VSG lint; Coverage / Synthesis / FuseSoC tests on the AWS runner for PRs to `main`).

## Phase Overview

```
1) Proposal & interface       → issue / proposal note + entity declaration
2) RTL implementation         → src/<area>/vhdl/olo_<area>_<function>.vhd
3) Testbench                  → test/<area>/olo_<area>_<function>/olo_<area>_<function>_tb.vhd
                                + sim/test_configs/olo_<area>.py entry
4) Documentation              → doc/<area>/olo_<area>_<function>.md
                                + doc/EntityList.md entry
5) Integration                → compile_order.txt regenerated
                                + Changelog.md entry
                                + tools/inference_test/yaml/<area>.yml entry (optional)
6) Verification & lint        → full regression on GHDL (and NVC if installed)
                                + VSG lint clean
                                + Coverage check (if Questa is available)
```

Track progress with a checklist (in the conversation, not on disk):

```
Entity: olo_<area>_<function>
- [ ] Phase 1: Proposal & entity declaration approved
- [ ] Phase 2: RTL implemented
- [ ] Phase 3: Testbench passing on GHDL
- [ ] Phase 4: Documentation written, entity added to EntityList
- [ ] Phase 5: compile_order / Changelog / inference-test entries added
- [ ] Phase 6: Full regression green, lint clean
```

**Hard rule — present every phase's deliverable to the user and wait for explicit approval before moving to the next phase.** Do not chain phases automatically.

---

## Repository Layout (what every entity touches)

Open Logic is organised by **area**, not by per-module folder. A single new entity touches files in five trees:

| Tree | Per-entity file | Notes |
| --- | --- | --- |
| `src/<area>/vhdl/` | `olo_<area>_<function>.vhd` | RTL source, single file per entity |
| `test/<area>/<entity-name>/` | `<entity-name>_tb.vhd` | VUnit testbench (folder named after the entity) |
| `sim/test_configs/` | append to `olo_<area>.py` | parameter sweep registered with VUnit |
| `doc/<area>/` | `<entity-name>.md` + entry in `doc/EntityList.md` | per-entity doc + ToC |
| `tools/inference_test/yaml/` | append to `<area>.yml` (optional) | synthesis inference for the entity |

Cross-cutting files updated once per entity:

| File | What to update |
| --- | --- |
| `compile_order.txt` | regenerated via `python sim/run.py --compile_list` (do **not** edit by hand) |
| `Changelog.md` | new bullet under the upcoming version |

Existing **areas** (see `doc/EntityList.md`):

| Area | Prefix | Contents |
| --- | --- | --- |
| `base` | `olo_base_*` | Clock crossings, RAMs, FIFOs, width converters, arbiters, pipeline stages, delays, CRC, strobe generators, reset generators, CAM, PRBS |
| `axi`  | `olo_axi_*`  | AXI4-Lite slave, AXI4 master (simple / full), AXI pipeline |
| `intf` | `olo_intf_*` | I²C master, SPI master/slave, UART, sync, debounce, clk-meas |
| `fix`  | `olo_fix_*`  | Fixed-point arithmetic + co-simulation utilities |
| `ft`   | `olo_ft_*`   | SECDED-protected fault-tolerant entities (RAMs, codec) |

If your entity does not fit any of these areas, propose a new area in Phase 1.

---

## Naming Conventions (extracted from `doc/Conventions.md`)

Read `doc/Conventions.md` for the full set. The hard rules are:

- **Entity:** `olo_<area>_<function>` (e.g. `olo_base_fifo_async`).
- **Generics:** `_g` suffix, PascalCase (e.g. `Width_g`, `RamStyle_g`).
- **Constants:** `_c` suffix.
- **Variables:** `_v` suffix.
- **Types:** `_t` suffix; FSM types `<name>Fsm_t` and FSM state values `_s` suffix.
- **Ports:** `<Interface>_<Signal>`, PascalCase, **no** `_i` / `_o` suffixes (direction is on the entity).
- **Library:** all sources are compiled into the `olo` library.
- **Language:** VHDL-2008. Use `library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;` (never `std_logic_arith` / `std_logic_unsigned`).
- **Reset:** synchronous, high-active, default `'0'`. Standard ports are `Clk` and `Rst`. For multi-clock entities use `<Domain>_Clk` / `<Domain>_Rst` (e.g. `In_Clk`, `In_Rst`, `Out_Clk`, `Out_Rst`).
- **AXI4-Stream style:** when a handshake is needed, expose `In_Valid` / `In_Ready` / `In_Data` (sink) and `Out_Valid` / `Out_Ready` / `Out_Data` (source). Open Logic supports back-pressure via the `UseReady_g` generic pattern (see `olo_base_pl_stage`).

---

## Phase 1: Interface & Architecture Proposal

Goal: lock down **WHAT** the entity does, **HOW** it looks from outside (interface), and **HOW** it is built on the inside (architecture) before any RTL is written. The interface and the internal block decomposition are the hardest things to change later, so this is where most of the design thinking happens.

> **Ask back frequently on architectural design decisions.** Phase 1 is collaborative by design. Whenever you face a real choice (primitive vs custom RTL, generic vs separate entity, sync vs async, where a pipeline register lives, etc.), present the options with their trade-offs and ask the user to pick rather than committing silently. Do not save up every decision for the end-of-phase review checkpoint; surface them in line as soon as they appear. A small number of mid-phase exchanges is cheaper than a Phase 2 RTL rewrite.

The deliverables of this phase are three short artefacts presented in the conversation (no files on disk yet):

1. Purpose & area note
2. Entity declaration
3. Architecture proposal (block diagram + internal entities + custom RTL list)

### Step 1a — Purpose & area

State, in two or three lines each:

- **Purpose:** what problem does the entity solve, and who would instantiate it. One or two sentences.
- **Area:** which of `base` / `axi` / `intf` / `fix` / `ft` the entity belongs to.
- **Comparable references:** the closest existing Open Logic entities. These inform both the interface style AND the architectural patterns (e.g. "shaped like `olo_base_fifo_async` but with a CRC tag per beat" or "wraps `olo_ft_ram_sp` plus a small scrubber FSM").

### Step 1b — Entity declaration

Draft the full VHDL `entity ... end entity;` declaration following the Open Logic naming rules. Include:

- Generics with type, default, and a one-line description for each.
- Ports grouped by function (clock/reset, primary in/out, optional side-channel, status outputs) with widths and defaults.
- A short note for each generic and each port group describing semantics (e.g. "synchronous to `Clk`", "default `'1'` for continuous reads", "tied to `'0'` when feature disabled").
- For handshake interfaces, use the canonical AXI4-Stream shape: `In_Valid` / `In_Ready` / `In_Data` (sink) and `Out_Valid` / `Out_Ready` / `Out_Data` (source). Use `UseReady_g` only if the entity supports a back-pressure-free fast path.
- For optional features that change the port list, decide between (a) a `Feature_g` generic with extra ports tied off when disabled, or (b) a separate `_<feature>` wrapper entity. Document the choice in step 1c.

Example shape (a typical AXI-Stream entity):

```vhdl
entity olo_<area>_<function> is
    generic (
        Width_g    : positive;
        Pipeline_g : natural range 0 to 2 := 0;
        UseReady_g : boolean              := true
    );
    port (
        -- Clock and Reset
        Clk        : in    std_logic;
        Rst        : in    std_logic;
        -- Input (AXI4-Stream sink)
        In_Valid   : in    std_logic                          := '1';
        In_Ready   : out   std_logic;
        In_Data    : in    std_logic_vector(Width_g - 1 downto 0);
        -- Output (AXI4-Stream source)
        Out_Valid  : out   std_logic;
        Out_Ready  : in    std_logic                          := '1';
        Out_Data   : out   std_logic_vector(Width_g - 1 downto 0)
    );
end entity;
```

### Step 1c — Architecture proposal

Sketch **how** the entity will be built. Three sub-deliverables:

**(1) Block diagram or data-flow description.** Show the major stages from input to output, the clock domain of each block, where the pipeline registers sit, and where back-pressure (if any) propagates. ASCII art works fine. Mark clock-domain crossings explicitly.

```
                       Wr_*                    Rd_*
                        │                        ▲
                        ▼                        │
                 ┌──────────────┐         ┌─────────────┐
                 │ user-priority│────────▶│  decoder    │
                 │   muxes      │         │ outputs tap │
                 └──────────────┘         └─────────────┘
                        │                        ▲
                        ▼                        │
                 ┌──────────────┐         ┌─────────────┐
                 │ olo_ft_ram_  │────────▶│ scrubber    │
                 │     sp       │   Dec_* │   FSM       │
                 └──────────────┘         └─────────────┘
```

**(2) Internal-entities table.** For every existing Open Logic entity you plan to instantiate, list the instance label, the entity name, and a one-line justification for why this specific primitive (instead of a hand-rolled equivalent or a different primitive).

| Instance | Entity | Why this one |
| --- | --- | --- |
| `i_ram`  | `olo_base_ram_sp`   | provides `RdValid` pipeline + BRAM inference |
| `i_enc`  | `olo_ft_ecc_encode` | SECDED encode on the write path             |
| `i_dec`  | `olo_ft_ecc_decode` | SECDED decode + `Out_Valid` alignment       |

This step forces the question "could a primitive replace something I was about to hand-write?" before any RTL exists. Use `doc/EntityList.md` to find candidates. For these patterns the right answer is almost always an existing base entity:

| Signal type | Use |
| --- | --- |
| Single-bit level(s) across clock domains | `olo_base_cc_bits` |
| Single-cycle pulse across clock domains | `olo_base_cc_pulse` |
| Multi-bit vector (slow updates) | `olo_base_cc_simple` / `olo_base_cc_status` |
| Multi-bit vector (handshake) | `olo_base_cc_handshake` |
| Continuous data stream | `olo_base_fifo_async` |
| Reset transfer | `olo_base_cc_reset` |
| Fixed-cycle delay of a vector | `olo_base_delay` |
| Configurable delay | `olo_base_delay_cfg` |
| Combinational/registered pipeline stage | `olo_base_pl_stage` |

Never roll your own 2-FF synchronizer on a multi-bit bus or a shift register where a primitive exists.

**(3) Custom RTL list.** For each piece of logic that will **not** be a primitive instantiation, list it with a one-line function description and a one-line "why custom" justification. Keep this list short on purpose; every entry is a place future review can push back.

| Custom block | Function | Why custom (no primitive fits) |
| --- | --- | --- |
| Port-arbitration muxes | Combinational mux picking user or scrubber source on shared port | Three concurrent assignments; no primitive applies |
| `RdValid` masking | AND-NOT of `Ram_RdValid` with `Scrub_Rd_Valid` to suppress scrubber-owned read pulses | Single gate; primitive would be overkill |
| Scrubber FSM | Address counter + 5-state RMW sequencer with collision-snoop logic | No suitable primitive in Open Logic; intentional new RTL |

State the **architectural trade-offs** that matter:

- Single entity with `Feature_g` generic, or separate `_<feature>` wrapper entity? Pick one, justify briefly.
- Sync only, or async clock support? If async, name the CDC primitives.
- Where does the read-valid (or other timing-critical) shift register live, and can it be shared with a sibling primitive?
- Any interface widening on a reused entity (e.g. adding `Rd_Valid` to `olo_base_ram_sp`) and the cost it imposes on existing callers.

### **REVIEW CHECKPOINT — STOP**

Present all three artefacts (purpose+area, entity declaration, architecture proposal) and explicitly ask the user to push back on:

- **Interface.** Do the port names and groupings match the area's conventions? Are generic defaults sensible? Is the AXI-Stream shape needed, or is a simpler one-shot interface enough?
- **Architecture.** Is each instantiated primitive the right choice? Is any "custom block" secretly an existing primitive in disguise? Are there cross-cutting choices (separate entity vs `_g` generic, sync-only vs async, shared vs duplicated shift registers) that warrant discussion now?
- **Trade-offs.** Are there obvious area or timing trade-offs hidden in the choices (extra shift register vs interface widening, mux depth vs separate ports, ...) that should be on the table before RTL gets written?

**Wait for explicit approval before continuing.** Iterate on the interface and the architecture together here. RTL changes in Phase 2 are cheap; interface and decomposition changes after Phase 2 are not.

---

## Phase 2: RTL Implementation

Write `src/<area>/vhdl/olo_<area>_<function>.vhd` using the approved entity declaration from Phase 1.

### File header

Every Open Logic source starts with the standard header:

```vhdl
---------------------------------------------------------------------------------------------------
-- Copyright (c) <year> by <author>
-- Authors: <author>
---------------------------------------------------------------------------------------------------

---------------------------------------------------------------------------------------------------
-- Description
---------------------------------------------------------------------------------------------------
-- <one-paragraph description matching the proposal>
--
-- Documentation:
-- https://github.com/open-logic/open-logic/blob/main/doc/<area>/olo_<area>_<function>.md
--
-- Note: The link points to the documentation of the latest release. If you
--       use an older version, the documentation might not match the code.
```

Copy the structure (libraries → entity → architecture) from a comparable existing entity rather than inventing one.

### Synchronous-design rules

- Edge-triggered FFs only — **never infer a latch**. Every `if` in a clocked process must have an `else`; every `case` must have `when others`.
- No combinational feedback loops — every feedback path passes through a register.
- No gated clocks — use clock enables (`if En = '1' then`).
- Single rising edge for all FFs within a clock domain.
- Provide a reset value for every register in the reset branch.

### Two-process design style

The two-process style is the **de-facto default** for Open Logic RTL. Use it for every new non-trivial entity. The full FIFO, AXI master, CRC, arbiter, width converter, CC, SPI, UART, I²C, debounce, CIC and divider entities all follow this pattern; mirror them.

**Structure.** All registers of the entity live as fields of a single `TwoProcess_r` record. The architecture has exactly two processes:

```vhdl
architecture rtl of olo_<area>_<function> is

    type TwoProcess_r is record
        -- every state-holding signal goes here (data, counters, FSM state, flags, ...)
        Counter : unsigned(...);
        Valid   : std_logic;
        ...
    end record;

    signal r, r_next : TwoProcess_r;

begin

    -- *** Combinatorial Process ***
    p_comb : process (all) is
        variable v : TwoProcess_r;
    begin
        v := r;                       -- hold variables stable

        -- ... combinational logic / FSM, writes to v.* ...

        r_next <= v;                  -- assign next-state at the very end
    end process;

    -- *** Sequential Process ***
    p_seq : process (Clk) is
    begin
        if rising_edge(Clk) then
            r <= r_next;
            if Rst = '1' then
                r.<state_field_1> <= <reset_value>;
                r.<state_field_2> <= <reset_value>;
                -- Only state-holding fields. Pipeline / data fields are NOT reset.
            end if;
        end if;
    end process;

end architecture;
```

Conventions inside this skeleton:

- The record type is named `TwoProcess_r`. The two signals are `r` (registered) and `r_next` (next-state).
- The variable inside `p_comb` is named `v`. Always start the process with `v := r;` so all fields hold their previous value unless explicitly overwritten.
- All combinational logic, including default assignments to ports/internal signals and the FSM, lives in `p_comb`. **Do not split a "next-state" process and an "output" process** — outputs are driven inside `p_comb` directly.
- End `p_comb` with `r_next <= v;` (no other assignments to `r_next`).
- `p_seq` only does `r <= r_next` plus an **end-of-process reset override** (matching the project-wide reset rule in `doc/Conventions.md`). Reset only the fields that hold genuine state; pipeline-only fields stay un-reset to keep reset fanout low.
- For multi-clock entities, replicate the pattern per clock domain (`r_in / r_in_next` driven by `In_Clk`, `r_out / r_out_next` driven by `Out_Clk`).

### FSM implementation

FSMs are **embedded inside the two-process record**, not implemented as a separate "next-state + state-register" pair of processes. Naming follows `doc/Conventions.md`:

- FSM type: `<name>Fsm_t` (e.g. `RdFsm_t`).
- State values: `_s` suffix (e.g. `Fetch_s`, `Data_s`, `Last_s`).
- The FSM state is a field of `TwoProcess_r` (e.g. `RdFsm : RdFsm_t;`).

The canonical shape (modelled on `olo_base_fifo_packet.vhd` and `olo_base_crc_append.vhd`):

```vhdl
-- Inside the architecture declaration
type RdFsm_t is (Fetch_s, Data_s, Last_s);

type TwoProcess_r is record
    ...
    RdFsm : RdFsm_t;
    ...
end record;

-- Inside p_comb
p_comb : process (all) is
    variable v : TwoProcess_r;
begin
    v := r;

    -- Default assignments for combinational outputs (each branch only overrides what it needs)
    Out_Valid <= '0';
    Out_Data  <= (others => 'X');

    case r.RdFsm is                          -- switch on the REGISTERED state
        when Fetch_s =>
            if start_condition then
                v.RdFsm := Data_s;
            end if;

        when Data_s =>
            Out_Valid <= '1';
            if end_condition then
                v.RdFsm := Last_s;
            end if;

        when Last_s =>
            Out_Valid <= '1';
            v.RdFsm := Fetch_s;

        -- coverage off
        when others => v.RdFsm := Fetch_s;   -- unreachable code, safe recovery
        -- coverage on
    end case;

    r_next <= v;
end process;

-- Inside p_seq reset branch
if Rst = '1' then
    r.RdFsm <= Fetch_s;
    ...
end if;
```

Specific rules to follow:

- The `case` is on **`r.<Fsm>` (the registered value)**, not `v.<Fsm>`. If subsequent logic in the same beat needs to know whether a transition was just decided, it can inspect `v.<Fsm>` directly.
- **No dedicated output-decoding process.** Outputs are driven combinatorially inside the case branches (Mealy where outputs depend on inputs, Moore where they only depend on `r.*` and are assigned outside the case). Set safe defaults before the `case` so each branch only overrides what it changes.
- Always end the `case` with `when others => v.<Fsm> := <default>_s;` wrapped in `-- coverage off` / `-- coverage on` pragma markers. This satisfies VHDL completeness, gives a safe-recovery path if synthesis ever produces an illegal state, and prevents the unreachable branch from counting against the 100 % coverage goal stated in `doc/Conventions.md`.
- Reset the FSM field to its initial state in the `p_seq` reset override branch alongside any other true state-holding fields.

### Reuse Open Logic building blocks

Before writing any FIFO, clock-crossing, width converter, pipeline stage, RAM, arbiter, CRC engine, or fixed-point math from scratch, look up the corresponding Open Logic entity in `doc/EntityList.md` and instantiate it. Ask back frequently on architectural design decisions. The CDC entities in particular are correctness-critical:

| Signal type | Use |
| --- | --- |
| Single-bit level(s) | `olo_base_cc_bits` |
| Single-cycle pulse | `olo_base_cc_pulse` |
| Multi-bit vector (slow updates) | `olo_base_cc_simple` / `olo_base_cc_status` |
| Multi-bit vector (handshake) | `olo_base_cc_handshake` |
| Continuous data stream | `olo_base_fifo_async` |
| Reset transfer | `olo_base_cc_reset` |

Never use a hand-written 2-FF synchronizer on a multi-bit bus — bits may arrive in different cycles.

### **REVIEW CHECKPOINT — STOP**

Present the RTL file to the user. Ask for review of:

- Algorithm correctness (does it implement what the proposal said?).
- Code-style adherence (`doc/Conventions.md`).
- Reuse of existing Open Logic entities.

**Wait for explicit approval before moving to Phase 3.**

---

## Phase 3: Testbench

Open Logic testbenches use **VUnit** plus the VUnit verification-components library
(`vunit_lib.vc_context`) — `axi_stream_master_t`, `axi_stream_slave_t`, etc. **Open Logic does not use UVVM.** Do not introduce UVVM into a contribution.

### File location

```
test/<area>/olo_<area>_<function>/olo_<area>_<function>_tb.vhd
```

### Skeleton

Use this skeleton (model copied from `test/base/olo_base_arb_prio/olo_base_arb_prio_tb.vhd`):

```vhdl
---------------------------------------------------------------------------------------------------
-- Copyright (c) <year> by <author>
-- Authors: <author>
---------------------------------------------------------------------------------------------------

library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

library vunit_lib;
    context vunit_lib.vunit_context;
    -- Add the next two only if you use AXI-Stream / com VCs:
    context vunit_lib.com_context;
    context vunit_lib.vc_context;

library olo;
    use olo.olo_base_pkg_math.all;
    use olo.olo_base_pkg_logic.all;

-- vunit: run_all_in_same_sim
entity olo_<area>_<function>_tb is
    generic (
        runner_cfg : string;
        -- Mirror the DUT generics you want to sweep over here.
        Width_g    : positive := 16
    );
end entity;

architecture sim of olo_<area>_<function>_tb is

    constant ClkPeriod_c : time := 10 ns;

    signal Clk : std_logic := '0';
    signal Rst : std_logic := '1';
    -- DUT-side signals here

begin

    Clk <= not Clk after 0.5 * ClkPeriod_c;

    i_dut : entity olo.olo_<area>_<function>
        generic map (
            Width_g => Width_g
        )
        port map (
            Clk => Clk,
            Rst => Rst
            -- ...
        );

    test_runner_watchdog(runner, 1 ms);

    p_control : process is
    begin
        test_runner_setup(runner, runner_cfg);

        while test_suite loop
            -- Reset between cases
            wait until rising_edge(Clk);
            Rst <= '1';
            wait for 200 ns;
            wait until rising_edge(Clk);
            Rst <= '0';
            wait until rising_edge(Clk);

            if run("Case-Basic") then
                -- stimulus + checks
            elsif run("Case-Stress") then
                -- ...
            end if;
        end loop;

        test_runner_cleanup(runner);
    end process;

end architecture;
```

### What to verify

At minimum:

- A **basic** test that exercises the nominal data path.
- **Reset behaviour** — assert/deassert mid-operation and check the entity recovers cleanly.
- **Edge cases** of every generic (min, max, default).
- **Back-pressure** for any AXI-Stream entity — exercise `Out_Ready` stalls using `axi_stream_slave_t` with a non-zero `stall_config`.
- **Random valid** for handshake interfaces — use `axi_stream_master_t` with and use random valid assertion in at least one testcase.
- **Coverage of every requirement** stated in the Phase-1 proposal.

If the entity has multiple clock domains, also sweep the source/destination clock ratios — see `sim/test_configs/olo_base.py` for the standard ratio set.

### Register the testbench with VUnit

Append a configuration block to `sim/test_configs/olo_<area>.py`:

```python
### olo_<area>_<function> ###
tb = olo_tb.test_bench('olo_<area>_<function>_tb')
for w in [8, 16, 32]:
    named_config(tb, {'Width_g': w})
```

### Run the tests

Use the central `sim/run.py` script. The simulator is selected via flag or `VUNIT_SIMULATOR`:

```bash
cd sim
python run.py "*olo_<area>_<function>*" -p 4
```

See the **Simulator support** section below for which simulator the workflow can pick.

### **REVIEW CHECKPOINT — STOP**

Show the user:

- Final TB source.
- Test-config snippet.
- The full passing log (test count, all PASS).

Ask for review of test coverage. **Wait for explicit approval before Phase 4.**

---

## Phase 4: Documentation

Every entity has a markdown doc at `doc/<area>/olo_<area>_<function>.md`. Open the closest comparable entity's doc and follow its structure exactly — it's intentional and tools (CI, badges, ToC) depend on it.

### Mandatory structure

```markdown
<img src="../Logo.png" alt="Logo" width="400">

# olo_<area>_<function>

[Back to **Entity List**](../EntityList.md)

## Status Information

![Endpoint Badge](https://img.shields.io/endpoint?url=https://storage.googleapis.com/open-logic-badges/coverage/olo_<area>_<function>.json?cacheSeconds=0)
![Endpoint Badge](https://img.shields.io/endpoint?url=https://storage.googleapis.com/open-logic-badges/branches/olo_<area>_<function>.json?cacheSeconds=0)
![Endpoint Badge](https://img.shields.io/endpoint?url=https://storage.googleapis.com/open-logic-badges/issues/olo_<area>_<function>.json?cacheSeconds=0)

VHDL Source: [olo_<area>_<function>](../../src/<area>/vhdl/olo_<area>_<function>.vhd)

## Description

<one or two paragraphs — same shape as the entity's RTL description header>

## Generics

| Name      | Type     | Default | Description                |
| :-------- | :------- | ------- | :------------------------- |
| Width_g   | positive | -       | ...                        |

## Interfaces

<split into subsections when there are multiple groups; e.g. Clock-and-Reset / Input / Output / Error Injection>

### Clock and Reset

| Name | In/Out | Length | Default | Description                                     |
| :--- | :----- | :----- | ------- | :---------------------------------------------- |
| Clk  | in     | 1      | -       | Clock                                           |
| Rst  | in     | 1      | '0'     | Reset (high-active, synchronous to _Clk_)       |

### Input

...

### Output

...

## Architecture

<short description + figure if helpful>

![architecture](./<area>/<function>/olo_<area>_<function>_arch.drawio.png)

## Constraints

<only if the entity needs TCL constraints>
```

Three coverage badges are mandatory — CI populates them when the first coverage run lands. Match the keys to the entity name exactly.

For architecture diagrams the project uses **draw.io** PNGs with the diagram XML embedded (`<name>.drawio.png`). Place per-entity figures under a subfolder (`doc/<area>/<group>/`) — never directly in the area folder, to keep the area folder uncluttered.

### Update EntityList

Add a one-line row for the new entity to the appropriate table in `doc/EntityList.md`. Keep the description short — the link points to the full doc.

### **REVIEW CHECKPOINT — STOP**

Present the doc + EntityList entry. **Wait for explicit approval before Phase 5.**

---

## Phase 5: Integration

These steps wire the new entity into the rest of the repository so CI sees it.

### 5a — Regenerate `compile_order.txt`

```bash
cd sim
python run.py --compile_list
```

The script writes the file at the repo root with forward slashes. **Never hand-edit it.** Verify the new entity appears in dependency order between its prerequisites and any RAM/FIFO it builds on.

### 5b — Append to `Changelog.md`

Add a bullet under the next-release heading describing the new entity in user-facing terms (what it does, key generics).

### 5c — Synthesis inference (optional but recommended)

If the entity is meant for users to instantiate directly, add one representative configuration to `tools/inference_test/yaml/<area>.yml`. Keep the configuration list short (typically one entry per entity) — synthesis runs on the AWS runner are not free.

### 5d — VHDL Language Server config (optional)

If `vhdl_ls.toml` needs the new file, regenerate it:

```bash
cd sim
python create_vhdl_ls_config.py
```

### **REVIEW CHECKPOINT — STOP**

Show the user the diff for `compile_order.txt`, `Changelog.md`, and (if touched) `tools/inference_test/yaml/<area>.yml`. **Wait for approval before Phase 6.**

---

## Phase 6: Verification & Lint

### 6a — Full regression on free simulators

The HDL-Check CI workflow runs **GHDL and NVC** for free contributions. Reproduce both locally if installed:

```bash
cd sim
python run.py -p 16              # default: GHDL
python run.py --nvc -p 16        # if NVC is installed
```

Both must pass before opening the PR. If only GHDL is installed, state that clearly when handing the result back to the user.

### 6b — VSG lint

Open Logic has three vsg configs under `lint/config/`:

| File | Used for | Notes |
| --- | --- | --- |
| `vsg_config.yml` | production VHDL **and** per-entity TBs in `test/<area>/<entity>/` | Compatible with vsg **3.25.0** (pin it: `python -m pip install vsg==3.25.0`). Preserves PascalCase. |
| `vsg_config_overlay_vc.yml` | **only** shared verification components under `test/tb/` | Forces `case: lower` (VUnit-VC style). **Do not apply this overlay to per-entity TBs.** |
| `fix_only_config.yml` | use with `--fix --fix_only` to apply *safe* auto-fixes only | Whitelist of whitespace / structure rules. Explicitly excludes case-changing rules. |

CI runs check-only (`--all_phases`, no `--fix`) via `lint/script/script.py`. Match that locally:

```bash
# Production source (always vsg_config.yml only)
vsg \
    --configuration ./lint/config/vsg_config.yml \
    --filename ./src/<area>/vhdl/olo_<area>_<function>.vhd \
    --all_phases

# Per-entity testbench (still vsg_config.yml only — no VC overlay)
vsg \
    --configuration ./lint/config/vsg_config.yml \
    --filename ./test/<area>/olo_<area>_<function>/olo_<area>_<function>_tb.vhd \
    --all_phases

# Shared VC under test/tb/ (overlay applies here)
vsg \
    --configuration ./lint/config/vsg_config.yml ./lint/config/vsg_config_overlay_vc.yml \
    --filename ./test/tb/<vc-file>.vhd \
    --all_phases
```

Fix every reported violation. **Be careful with `--fix`** — applied with `vsg_config.yml` alone it will auto-lowercase identifiers, which contradicts Open Logic's PascalCase convention. Two safe options:

1. Fix the reported violations **by hand** (preferred for entity declarations and ports — case must stay PascalCase).
2. Use the project's whitelist for whitespace-only auto-fixing:
   ```bash
   vsg --fix --fix_only ./lint/config/fix_only_config.yml \
       --configuration ./lint/config/vsg_config.yml \
       --filename <file> --all_phases
   ```
   This applies only the rules listed in `fix_only_config.yml` and leaves identifier casing untouched.

### 6c — Markdown lint

```bash
markdownlint -c .markdownlint.json doc/<area>/olo_<area>_<function>.md
```

### 6d — Coverage (only if Questa is available)

```bash
cd sim
python run.py --modelsim --coverage -p 4 "*olo_<area>_<function>*"
python AnalyzeCoverage.py
```

Skip this step on a free toolchain — the GitHub-runner workflow doesn't require it. The Coverage workflow on the AWS runner will catch any gaps.

### **FINAL CHECKPOINT**

Hand back to the user:

- Summary of regression results (which simulators, pass counts).
- VSG / markdownlint status.
- A draft of the contribution checklist they need to follow per `Contributing.md`:
  1. Fork the repo.
  2. Branch `feature/<your-feature-name>` from `develop`.
  3. Sign the [CLA](https://cla-assistant.io/open-logic/open-logic).
  4. Open the PR against `develop`.

---

## Simulator Support

Open Logic's `sim/run.py` recognises three simulators via the `vunit.Simulator` enum:

| Simulator | License | `run.py` flag | `VUNIT_SIMULATOR` value | Coverage support |
| --- | --- | --- | --- | --- |
| **GHDL** | open-source | `--ghdl` (default) | `ghdl` | no (in this flow) |
| **NVC** | open-source | `--nvc` | `nvc` | no (in this flow) |
| **ModelSim / Questa Intel FPGA Starter** | commercial (free starter edition available) | `--modelsim` | `modelsim` | yes (`--coverage` requires this) |

Other simulators VUnit supports (Riviera-PRO, Active-HDL) are **not exercised by Open Logic CI** — do not assume they work.

### Detect what's installed before recommending a simulator

When this skill needs to pick a simulator (running the regression in Phase 3, 6a, or 6d), detect available tools via `shutil.which`. Use this snippet (or call it from a small helper):

```python
import shutil

def detect_simulators():
    """Return a dict mapping our run.py keys to the binary path actually found.

    None of the entries are needed for parsing — we just want to know which
    `run.py` flag is safe to use on this workstation.
    """
    sims = {}
    if shutil.which("ghdl"):
        sims["ghdl"] = shutil.which("ghdl")
    if shutil.which("nvc"):
        sims["nvc"] = shutil.which("nvc")
    # ModelSim / Questa both ship `vsim`. Distinguish via version banner.
    vsim = shutil.which("vsim")
    if vsim:
        sims["modelsim"] = vsim
    return sims
```

Selection priority for the skill:

1. If `GHDL` is found → use it (matches the CI default; fastest free path).
2. Else if `NVC` is found → use it (CI's secondary free simulator).
3. Else if `vsim` is found → use `--modelsim`.
4. Else → tell the user no supported simulator is on PATH and link to `doc/HowTo.md` §"Run Simulations".

Coverage runs (Phase 6d) require `vsim`. If it's absent, skip the coverage step and say so explicitly — the user's PR will still pass HDL-Check on GitHub.

### VUnit installation

VUnit itself is required regardless of simulator: `python -m pip install vunit_hdl`. The `run.py` script also expects `osvvm` for randomisation in some tests — `vu.add_osvvm()` covers that.

---

## When NOT to use this skill

- **Bug fixes in an existing entity.** Use `open-logic-dbg` to triage, then patch the RTL / TB / doc directly. The six-phase ramp-up is overkill.
- **Documentation-only changes.** Edit the relevant `doc/**/*.md` file and rerun `markdownlint`.
- **Adding a new test case to an existing TB.** Just append the `elsif run("…")` block and (if needed) a new config in `sim/test_configs/olo_<area>.py`.

---

## Reference entities (recommended templates)

| Pattern | Good template entity |
| --- | --- |
| Plain combinational + register | `olo_base_pl_stage` |
| AXI4-Stream sink + source with back-pressure | `olo_base_wconv_n2m` |
| Multi-clock-domain entity | `olo_base_fifo_async`, `olo_base_cc_handshake` |
| Single-port RAM wrapper | `olo_base_ram_sp` (and `olo_ft_ram_sp` for the ECC wrap pattern) |
| Package-only contribution | `olo_base_pkg_logic`, `olo_ft_pkg_ecc` |

When starting a new entity, **always** open the closest template first and mirror its file structure, header style, and TB layout.
