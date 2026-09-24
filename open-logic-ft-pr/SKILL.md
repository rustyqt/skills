---
name: open-logic-ft-pr
description: >-
  Workflow for contributing Open Logic fault-tolerant (ft) entities upstream. Explains how the
  rustyqt backlog branch (feature/fault-tolerant-all-entities), the upstream-staging branch
  (feature/fault-tolerant), and the open-logic/open-logic upstream PR (#294) relate, and how to
  stage the next per-feature PR by cherry-picking from the backlog. Use this whenever the user is
  working on the ft merge/PR flow: porting an olo_ft_* entity toward upstream, opening or
  refreshing the upstream fault-tolerant PR, cherry-picking ft features between the rustyqt
  branches, deciding what belongs in the next FT PR, reconciling with the maintainer's RdEna/RdValid
  PR #315, or asking about the ft merge status or where ft work should land. Covers branch roles,
  the per-PR porting checklist, verification (GHDL regression + vsg + inference test), and the
  cross-cutting ft API decisions. Reach for this skill even when the user does not say "PR" by
  name but is clearly moving ft work toward upstream.
---

# Open Logic Fault-Tolerant PR Workflow

This skill covers moving *finished* fault-tolerant (`ft`) entities to the upstream Open Logic
project. When the user asks to **develop** a new entity (design, RTL, testbench), use the
`open-logic-dev` skill; to run the synthesis inference test on this host, use the
`open-logic-inference-test` skill. This skill picks up once an entity is built and ready to port.

It is workflow guidance; live status lives in a companion tracker:

- **`merge_status.md`** (bundled in this skill's directory) — the per-PR tracker: what is queued,
  what is merged, open review questions. Treat it as the source of truth for *current* status; this
  SKILL.md is the source of truth for *process*. Re-read it and reconcile against `git log` before
  acting, since status drifts.

## Branch topology (where ft work lives)

ft work lives in two branches of the `rustyqt/open-logic` fork, feeding the upstream project:

| Role | Location | Purpose |
| --- | --- | --- |
| **Backlog / integration** | `rustyqt/open-logic @ feature/fault-tolerant-all-entities` | Comprehensive branch holding **all** ft entities. New ft development and integration happen here. The full GHDL regression passes here — it is the green reference. |
| **Upstream staging** | `rustyqt/open-logic @ feature/fault-tolerant` | Curated branch from which upstream PRs are cut, **one feature at a time**. Also receives the maintainer's own PRs (e.g. #315). Should mirror what is under upstream review. |
| **Upstream PR target** | `open-logic/open-logic` (PR [#294](https://github.com/open-logic/open-logic/pull/294)) | PRs target the upstream **`feature/fault-tolerant`** branch until the whole series is reviewed; release to `develop` only after. |

Remotes: the local clone's `origin` is `rustyqt/open-logic`. `open-logic/open-logic` is a separate
fork — upstream PRs are cross-fork PRs created on GitHub (there is usually no `upstream` git remote
configured locally).

## The golden rule

The maintainer agreed to review the ft series **one PR at a time** against upstream
`feature/fault-tolerant`. Everything below serves that constraint. Do not front-run it by dumping
the entire backlog upstream or into the staging branch at once.

## Backlog commit conventions

Clean cherry-picking depends on how the backlog is committed. Keep to these conventions on
`feature/fault-tolerant-all-entities`:

- **One logical change per commit**, dependency-ordered (a prerequisite lands before what needs it —
  e.g. the TMR CDC primitives before the `FaultTolerant_g` change that instantiates them).
- **Source, testbench and `doc/ft/*.md` travel together** in the entity's commit.
- **Shared build/index files** (`compile_order.txt`, `sim/test_configs/olo_ft.py`,
  `tools/inference_test/yaml/ft.yml`, `doc/EntityList.md`, `src/ft/olo_ft_dev.core`) are bundled in a single trailing
  integration commit, not split across feature commits. Consequence: a feature commit on its own
  does not build — the per-PR port re-derives that feature's integration slice (Staging step 4).
- **Message prefixes** match the repo: `FEATURE:` (new entity), `IMPROVEMENT:` (enhance existing),
  `TEMPORARY:` (stop-gap to be superseded), plus `DOC:` / `TEST:` / `STYLE:` / `BUGFIX:`.
- Commits are authored on the user's behalf with **no co-author trailer**, and only on explicit
  request.
- Keep the backlog tip **green** (full GHDL regression passes) before and after adding a feature.

## Staging the next upstream PR

Bring features into the staging branch by **cherry-picking** the specific feature commit(s) from the
backlog — one feature at a time, never by merging the backlog branch wholesale. The backlog commits
are kept granular (roughly one feature per commit) so they cherry-pick cleanly. A few backlog commits
are coarser than the per-PR plan (e.g. one commit covers `ram_sdp` + `ram_tdp`, one covers all three
FIFOs) — split those with file-level cherry-picks when porting.

1. **Pick the next feature** from the queue in `merge_status.md`.
2. **Sync the staging branch first.** Ensure local `feature/fault-tolerant` matches upstream and
   already contains any maintainer base changes it depends on — most importantly **PR #315** (see
   below). Build ft RAM wrappers on top of the *official* base interface, not the temporary shim.
3. **Cherry-pick** the feature's commit(s) from the backlog onto `feature/fault-tolerant`. Resolve
   conflicts against the maintainer's base.
4. **Per-PR boilerplate** (these files are shared, so each PR appends its own slice):
   - append the entity block to `sim/test_configs/olo_ft.py`
   - append the entity block to `tools/inference_test/yaml/ft.yml` — since PR #320 CI runs
     `InferenceTest.py --yml=./yaml/ft.yml --check-coverage` (`.github/workflows/synthesis.yml`), so
     every entity in `src/ft/vhdl` must be either configured or excluded; name private helpers
     `olo_ft_private_*` so the standing wildcard exclude covers them (no exact-name entries)
   - add the entity row(s) to `doc/EntityList.md` (private helpers get a doc page but no row)
   - regenerate `compile_order.txt` (`python sim/run.py --compile_list`); normalize backslashes on
     Windows
   - regenerate `src/ft/olo_ft_dev.core`: `cd tools/fusesoc` then
     `python UpdateCoreFiles.py --version <current> --cl-fix-version <current>` (versions from the
     `name :` lines of the existing cores). The script regenerates ALL areas, tutorials and the
     `en_cl_fix` submodule — `git checkout --` the churn in every other core and
     `git -C 3rdParty/en_cl_fix checkout -- en_cl_fix_dev.core`. **Never add or modify
     `tools/fusesoc/stable/*.core` in a feature PR**: stable cores pin a published release tag
     (which has no `src/ft`) and are generated only by the maintainer's release commit.
   - commit the entity's `doc/ft/*.md` alongside its source and testbench
5. **Verify** before opening/refreshing the PR (see Verification).
6. **Open or refresh** the cross-fork PR to upstream `feature/fault-tolerant`, then record it in
   `merge_status.md`. Note: a push that touches `.github/workflows/*` is rejected unless the GitHub
   token has the `workflow` OAuth scope — fix with `gh auth refresh -h github.com -s workflow`
   (interactive browser step, ask the user to run it).

## The PR #315 interaction (read before touching base RAMs)

The maintainer's PR [#315](https://github.com/open-logic/open-logic/pull/315) adds `RdEna` and
`RdValid` to **all** base RAMs and is destined for `feature/fault-tolerant`. The backlog contains a
`TEMPORARY:` commit that adds `Rd_Valid` to `olo_base_ram_sdp/tdp` as a stop-gap so the ft wrappers
could be developed before #315 landed.

Consequence: **do not cherry-pick the temporary base-RAM commit into the staging branch as-is.** Once
#315 is in `feature/fault-tolerant`, the official `RdEna`/`RdValid` interface supersedes the shim.
Rebase the ft RAM/scrub wrappers onto #315's interface and drop the temporary base change. This is
why that commit is labelled `TEMPORARY`.

## Verification (run before opening/refreshing a PR)

- **Functional (default GHDL):** full regression with `python sim/run.py -p 16` from the repo root.
  GHDL is the default for all day-to-day work and runs the whole suite in ~2 min; the backlog
  reference passes at 5020/5020 — keep it green.
- **Functional (ModelSim, only when explicitly asked):** ModelSim Pro ships with the Libero install,
  but `vsim.exe` is not on PATH and the host has a single ModelSim licence. Prepend the bin dir and
  run single-process (`-p 16` would spawn 16 vsim instances, 15 of which fail to get the licence):

  ```powershell
  $env:PATH = "D:\Microchip\Libero_SoC_2025.2\Libero_SoC\ModelSim_Pro\win32acoem;$env:PATH"
  python sim\run.py --modelsim -p 1
  ```

  The full FT regression takes ~15 min under ModelSim `-p 1`. If a previous run hangs holding the
  licence, kill leftovers first:

  ```powershell
  Get-Process | Where-Object { $_.ProcessName -match 'vsim|vcom|vlog|vish' } | Stop-Process -Force
  ```
- **Lint:** `vsg --all_phases` clean on every changed `olo_ft_*`/`olo_base_*` source and testbench,
  plus markdownlint on docs.
- **Synthesis inference:** since PR #320 the ft area is part of the CI synthesis workflow
  (`synthesis.yml` runs `ft.yml` with `--check-coverage` on the AWS runner), so a local Libero run is
  a pre-check rather than the only line of defense — see the `open-logic-inference-test` skill for
  the apply/run/revert workflow. `tools/inference_test/yaml/ft.yml` keeps one representative config
  per entity to keep CI reasonable; private `olo_ft_private_*` entities are wildcard-excluded.

## Cross-cutting ft API decisions

Every ECC-protected entity shares a locked API (paired `ErrInj_BitFlip`/`ErrInj_Valid` injection,
`*EccSec`/`*EccDed` status outputs, `RamRdLatency_g`, `RdValid`, the AXI-S codec architecture, the
scrubber's `Scrub_Inhibit`/`Scrub_Rd_*` surface). These are already applied across the backlog, so
porting is mechanical. The authoritative write-up of *why* the API looks the way it does lives in
the "Cross-cutting API decisions" section of the bundled `merge_status.md` — read it before
answering reviewer questions about port naming or injection semantics.

## Scrubbing concept (resolved)

Scrubbing is implemented as **separate `olo_ft_ram_*_scrub` wrapper entities** (not a generic on the
RAM), using opportunistic scheduling and a private reusable scrubber FSM (`olo_ft_private_scrubber`,
renamed from `olo_ft_ram_scrubber` in the PR #320 review round so the `olo_ft_private_*` wildcard
exclude covers it — standalone private files follow the `olo_<area>_private_*` naming).
That is the current, settled approach — see `merge_status.md` for the resulting port surface.
