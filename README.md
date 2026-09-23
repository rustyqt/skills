# Claude Code skills

A small collection of [Claude Code](https://claude.com/claude-code) skills I use day-to-day. Each
subdirectory is one skill — drop it into a project's `.claude/skills/` folder (or your global
`~/.claude/skills/`) and Claude will discover it on the next session.

## Skills

| Skill | Purpose |
| --- | --- |
| [`open-logic-dev`](./open-logic-dev) | Six-phase workflow for adding a new entity to the [Open Logic](https://github.com/open-logic/open-logic) VHDL library. Proposal → entity declaration → RTL → testbench → documentation → integration, with a user-review checkpoint at the end of every phase. |
| [`open-logic-dbg`](./open-logic-dbg) | Diagnose-fix-verify loop for failing or unexpected Open Logic VUnit testbenches. Includes a `wavequery.py` CLI for VCD / WLF inspection across GHDL, NVC and ModelSim / Questa. |
| [`fpga-module-dev`](./fpga-module-dev) | Six-phase workflow for developing a new FPGA module in a project repository: requirements → architecture & design description → verification plan → RTL → testbenches → verification. Uses VUnit + UVVM, Open Logic as the design library (git submodule), and QuestaSim as the simulator. |
| [`fpga-module-dbg`](./fpga-module-dbg) | Diagnose-fix-verify loop for failing VUnit + UVVM testbenches in a project repository. Maps each root cause to the right `fpga-module-dev` phase, and ships the same `wavequery.py` CLI for VCD / WLF inspection across GHDL, NVC and ModelSim / Questa. |
| [`spacefibrelight-dev`](./spacefibrelight-dev) | Issue-driven workflow for bug fixes, standard-compliance changes and new modules in the CNES [SpaceFibre Light](https://github.com/CNES/spacefibrelight) IP, following the repo's own practices: understand the issue → agree the plan → implement and test in a cocotb scenario (bugs reproduced first) → dual-target (Versal + NG-Ultra) regression and PR to `develop`. Encodes the repo's unwritten conventions (naming, VHDL-93, CDC patterns, hand-maintained file lists) and adds no new requirement schemes or documentation. |
| [`drawio`](./drawio) | Generate native `.drawio` diagrams (flowcharts, architecture, ER, sequence, class, network, wireframes) as mxGraphModel XML, with optional PNG / SVG / PDF export via the draw.io desktop CLI. Upstream: [jgraph/drawio-mcp](https://github.com/jgraph/drawio-mcp/tree/main/skill-cli). |
| [`wavedrom`](./wavedrom) | Generate WaveDrom diagrams as WaveJSON (`.json5`): digital timing waveforms (SPI, I2C, AXI, handshakes, clock-with-enable), bitfield / register layouts, and gate-level logic schematics. Optional SVG / PNG / PDF export via [`wavedrom-cli`](https://github.com/wavedrom/wavedrom-cli). |

## Installation

```bash
# Per-project (from your project root)
git clone https://github.com/rustyqt/skills.git .claude/skills

# Or globally for every project
git clone https://github.com/rustyqt/skills.git ~/.claude/skills
```

`wavequery.py` (shipped with both `open-logic-dbg` and `fpga-module-dbg`) needs Python with `vcdvcd`:

```bash
python -m pip install vcdvcd
```

## Scope

The FPGA skills come in three flavours: **Open Logic-specific**, **generic FPGA project**, and **SpaceFibre Light-specific**.

### Open Logic skills (`open-logic-dev`, `open-logic-dbg`)

Tailored to the [Open Logic](https://github.com/open-logic/open-logic) library's conventions:

- Repository layout: `src/<area>/vhdl/`, `test/<area>/<entity>/`, `doc/<area>/`, `sim/test_configs/`.
- Naming: `olo_<area>_<function>` entities, PascalCase generics / ports.
- Test framework: **VUnit** (no UVVM).
- Simulator priority: **GHDL → NVC → ModelSim / Questa Intel Starter**.
- Linting: VHDL Style Guide (`vsg`) via `lint/config/vsg_config.yml`.

### FPGA module skills (`fpga-module-dev`, `fpga-module-dbg`)

Tailored to FPGA project repositories that consume Open Logic as a dependency:

- Repository layout: `hdl/<module>/{src,tb,docs}/`, with `open-logic/` and `uvvm/` as git submodules at the repo root, plus `constraints/`, `docs/`, `tcl/`, and `run.py`.
- Naming: snake_case module names, AXI-Stream / AXI-Lite for interfaces, `rst_n` active-low reset.
- Test framework: **VUnit + UVVM** (VVCs, BFMs, `t_rand`, `func_cov_pkg`).
- Simulator: **QuestaSim** (`VUNIT_SIMULATOR=modelsim`); GHDL not supported.
- Linting: VHDL Style Guide (`vsg`) via `.vscode/vsg.yaml`.

### SpaceFibre Light skill (`spacefibrelight-dev`)

Tailored to the [CNES/spacefibrelight](https://github.com/CNES/spacefibrelight) repository, which has no written
contribution guide. The conventions in the skill are extracted from its code, README, CI and issue / PR history:

- Repository layout: `src/module_data_link/`, `src/module_phy_plus_lane/` (Versal) and `src/module_phy_plus_lane_64b/`
  (NG-Ultra), `sim/scenario/<name>/` cocotb scenarios on `sim/benches/configuration_2_bench`.
- Naming: `G_` / `C_` prefixes, UPPER_SNAKE ports suffixed with the producing module's abbreviation, `_ST` FSM states,
  `--!Req: <ECSS clause>` traceability tags.
- Language: VHDL-93 compatible, single-process style with async active-low `RST_N`; no Open Logic.
- Test framework: **cocotb 1.9.x** + Elsys cocotb framework (submodule); system-level scenarios on `configuration_2_bench`.
- Traceability: only what the repo already uses (ECSS-E-ST-50-11C clause numbers, `--!Req:` tags, README datasheet
  sections); no extra documents beyond the existing README / `doc/` files.
- Simulator: **Questa** only; every change is regressed on both `HARDWARE_TARGET=VERSAL` and `NG_ULTRA`.
- CI: Linty only (no compile / simulation gate), so the local regression is mandatory.

If you adapt any of these skills for a different project, the structural rules and naming conventions are the
first things you'll want to change.

## License

MIT.
