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

The skills come in two flavours: **Open Logic-specific** and **generic FPGA project**.

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

If you adapt either pair for a different project, the structural rules and naming conventions are the
first things you'll want to change.

## License

MIT.
