# Claude Code skills

A small collection of [Claude Code](https://claude.com/claude-code) skills I use day-to-day. Each
subdirectory is one skill — drop it into a project's `.claude/skills/` folder (or your global
`~/.claude/skills/`) and Claude will discover it on the next session.

## Skills

| Skill | Purpose |
| --- | --- |
| [`open-logic-dev`](./open-logic-dev) | Six-phase workflow for adding a new entity to the [Open Logic](https://github.com/open-logic/open-logic) VHDL library. Proposal → entity declaration → RTL → testbench → documentation → integration, with a user-review checkpoint at the end of every phase. |
| [`open-logic-dbg`](./open-logic-dbg) | Diagnose-fix-verify loop for failing or unexpected Open Logic VUnit testbenches. Includes a `wavequery.py` CLI for VCD / WLF inspection across GHDL, NVC and ModelSim / Questa. |

## Installation

```bash
# Per-project (from your project root)
git clone https://github.com/rustyqt/skills.git .claude/skills

# Or globally for every project
git clone https://github.com/rustyqt/skills.git ~/.claude/skills
```

`wavequery.py` (used by `open-logic-dbg`) needs Python with `vcdvcd`:

```bash
python -m pip install vcdvcd
```

## Scope

Both skills are tailored to the **Open Logic** project's conventions:

- Repository layout: `src/<area>/vhdl/`, `test/<area>/<entity>/`, `doc/<area>/`, `sim/test_configs/`.
- Naming: `olo_<area>_<function>` entities, PascalCase generics / ports.
- Test framework: **VUnit** (no UVVM).
- Simulator priority: **GHDL → NVC → ModelSim / Questa Intel Starter**.
- Linting: VHDL Style Guide (`vsg`) via `lint/config/vsg_config.yml`.

If you adapt them for a different VHDL project, the structural rules and naming conventions are the
first things you'll want to change.

## License

MIT.
