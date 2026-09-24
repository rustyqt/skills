# Open Logic — Fault-Tolerant Merge Status

Per-PR tracker for porting fault-tolerant (`ft`) entities from the backlog branch
(`rustyqt/open-logic @ feature/fault-tolerant-all-entities`) into the upstream-staging branch
(`rustyqt/open-logic @ feature/fault-tolerant`), one PR at a time, and from there to the upstream
project `open-logic/open-logic` (PR [#294](https://github.com/open-logic/open-logic/pull/294)).

This file is the source of truth for **status**; the `SKILL.md` next to it is the source of truth
for **process**. Status drifts — reconcile against `git log` before acting.

**Host note (2026-08-28):** the work moved from the Windows host `Compucat` to this Linux host.
Paths written as `D:/git/X` throughout this file map to `~/git/X`. The three checkouts are
`~/git/open-logic` (backlog), `~/git/open-logic-syncfifo` (PR #335) and `~/git/open-logic-scrubber`
(PR #320). Toolchain setup and its gotchas are in the `sim-toolchain-ethereum` memory. The Libero
inference test does NOT run here (Windows-only, licensed on `Compucat`).

_Update 2026-08-28 — **PR #335 BACK-APPLIED to the backlog and EXTENDED to `olo_ft_fifo_async`;
backlog tip `03cd3f8`, pushed to `origin`.** One commit, 19 files. The two PR FIFOs were copied
byte-identical from the PR worktree (`D:/git/open-logic-syncfifo`) — RTL, TBs, docs, packet
diagram; `EntityList.md`, `olo_ft.py` and `ft.yml` were patched instead of copied because the
backlog carries more ft entities (the EntityList ft-FIFO intro deliberately OMITS the PR branch's
"an asynchronous variant will be introduced as well" sentence — the backlog already has it).
**`olo_ft_fifo_async` had the same defect and got the same fix**: it exposes the full status
surface on both sides and instantiated its decoder with `Pipeline_g => EccPipeline_g`, so with a
pipeline its read-side status described the internal FIFO, not the entity. Generic dropped,
`Pipeline_g => 0`, TB generic removed (the two `0 to 6 + EccPipeline_g` flush loops in
`ResetInFlight` become `0 to 6`, i.e. exactly the previously passing `EccPipeline_g=0` timing),
`olo_ft.py` sweep removed, `ft.yml` config `w32-ecc1` -> `w32`, doc generic row removed + the same
shared "Combinational ECC Encoder and Decoder" chapter as the other two. Its architecture diagram
needed NO redraw (decoded the embedded mxGraphModel: signal and entity names only, no generics).
**Collateral: both AXI masters lost `EccPipeline_g` too** — `olo_ft_axi_master_simple`/`_full`
forwarded their own copy into their two internal `olo_ft_fifo_sync` buffers, so the branch would
not elaborate otherwise. Verified first that neither master exposes any FIFO level or flag (only
ECC status + injection), so it was a pure timing knob; removed from RTL, both TBs, the two
`olo_ft.py` sweeps, the two `ft.yml` configs and both doc generic tables. The alternative (keep the
knob via an internal `olo_base_pl_stage` per buffer) was NOT implemented — it is new design work,
not a back-apply; flagged to the user, still open if the knob is ever wanted back. **`EccPipeline_g`
now survives only where it is correct**: the five RAMs (flags realigned through the `RdValid`
pipeline) and the two delays (no status surface at all). Verified: full regression
**6810/6810** (30 below the previous 6840 — the async sweep lost two of its three configs at ten
cases each), vsg 3.27 = 0 violations on all changed VHDL, markdownlint = 0 on all changed docs._

_Update 2026-08-27 — **PR #335 first review round ANSWERED, then the design was SIMPLIFIED; branch
tip `0d66d03`, pushed.** The round (12 inline comments, sync FIFO only) was first answered by
`ffb5f13` (read-side status via a counting entity `olo_private_ft_fifo_status`, `Out_Level` widened to
`log2ceil(Depth_g + 2*EccPipeline_g + 1)`). Reviewing `olo_ft_fifo_packet` afterwards showed the
pipeline ALSO breaks `Out_Next`/`Out_Repeat` there and that part is **not** correctable from the
wrapper: the base FIFO samples them on its own output handshake, which runs ahead of the observed
beats, and the repeat state needed to compensate (`r.RdRepeat`) is internal. `PacketLevel` has the
same defect. **Decision (user): force `Pipeline_g = 0` on both codecs in BOTH FIFOs and drop
`EccPipeline_g` entirely** (`0d66d03`, supersedes `ffb5f13`). Removed: `EccPipeline_g`,
`olo_private_ft_fifo_status`, the widened `Out_Level`, the packet FIFO's sideband bundle + internal
`olo_base_pl_stage`, and the `Out_Next`/`Out_Repeat` caveat. Both entities are now three
instantiations only; all levels/flags come straight from the internal FIFO, bit-identical to the base
entities, so drop-in replacement is exact again. Docs carry a shared "Combinational ECC Encoder and
Decoder" chapter recommending an EXTERNAL `olo_base_pl_stage` for timing (register data + ECC flags
+ Last/Size together; note that `Out_Next`/`Out_Repeat` then refer to the beat inside that stage).
**Justified by Fmax measurement** (Libero, MPFS250T, pl_stage harness, archived under the
inference-test skill `fmax-results/fifo-sync` + `fifo-packet`): sync 153.2/171.5/226.6 MHz at
EccPipeline 0/1/2; packet 154.9/167.0/176.1 — the packet FIFO plateaus because its decoder was
combinational and `EccPipeline_g` only drove the bundled pl_stage, so both stages sat in series AFTER
the decode (critical path ends at stage 0 in both cases). Critical path always starts at the RAM
output. **TB**: kept the `ffb5f13` work (Empty/Out_Valid + Full/In_Ready monitors, parity cases vs
`olo_base_fifo_sync_tb`, sweeps `Depth_g`/`AlmFullOn_g`/`AlmEmptyOn_g`/`RamBehavior_g`/
`ReadyRstState_g`); packet TB gained `NextPacket` (Out_Next had ZERO coverage), 
`PacketLevelAndFreeWords`, `Size1Packets`, `Wraparound`, `ResetState` — the base packet suite's 49-case
drop/repeat/next permutation matrix was deliberately NOT mirrored (exercises base machinery the wrapper
does not touch; offered to the maintainer). All 12 maintainer threads answered incl. a supersession note
in the level thread. Verified: regression **6199/6199**, vsg 3.27 = 0 (4 files), markdownlint = 0.
Gotchas learned: (a) a `natural range` counter in `p_comb` bound-checks on transient combinational
evaluations, guard both directions like `olo_base_fifo_sync` does; (b) `olo_ft_ecc_decode` and
`olo_base_pl_stage` are handshake-identical for equal stage counts (data-independent FSM, Mid_Valid/
Mid_Ready wired straight), so a parallel decode needs no join logic; (c) for bottom-edge diagram runs
going LEFT the leftmost exit must take the highest label, mirrored for rightward runs._

_Update 2026-08-08 — **NEW ENTITIES: olo_ft_ecc_monitor + olo_ft_ecc_monitor_axi** (3 commits
`0fe83b1..64aa32d` on the backlog, pushed; PR-ready, queue after the existing backlog). EDAC
monitor core: per-channel saturating SEC/DED counters (CounterWidth_g 1..16, Channels_g 1..255),
sticky DED flags, Evt_Sec/Evt_Ded pulses, RAM-style read port (latency 1) with atomic
read-and-clear; clear precedence sample->clear->count (no lost events); FF counter file by
necessity (simultaneous multi-channel events) => NO ErrInj ports (first ft entity without — no
codeword inside; documented). AXI wrapper: olo_axi_lite_slave + register decode + core; map INFO/
CTRL/IRQ_STATUS(W1C)/IRQ_ENA/DED_STICKY_k/CNT_ch (Sec[15:0]|Ded[31:16], any write clears channel
via core Rd_Clr); unmapped reads answered by the slave read timeout (library pattern); counter
reads through the core read port (no shadow copies). User decisions honored: In_Valid (not
In_Qual), 16-bit counter cap, resettable counters, SEC_STICKY dropped (DED sticky only). Arch
diagram for the wrapper in sp_scrub container style (`doc/ft/monitor/`). TB gotchas: the AXI
master VC runs write/read channels concurrently — `wait_until_idle` needed between order-sensitive
ops; vsg process_026/027 forbid blanks around in-process declaratives — TB subprograms live at
architecture level with signal params (scrubber precedent). Verified: 96/96 monitor tests, full
regression **6788/6788**, vsg 3.27 = 0 (4 files), markdownlint = 0. Local Libero inference for the
new ft.yml entries not run (CI covers toward main). 2026-08-09 (`d5e8c32`, pushed): **DED_STICKY_k
registers REMOVED** from the wrapper per user decision (counters suffice at register level) — map
is now INFO/CTRL/IRQ_STATUS/IRQ_ENA + CNT_ch at fixed CNT_BASE 0x10; the core keeps its DedSticky
PORT (wrapper leaves it open; documented as available for fabric-side safing logic); diagram
updated in place; regression 6785/6785 (DedSticky AXI TB case removed), vsg + markdownlint 0._

_Update 2026-08-06 (c) — **PR #335 OPENED (sync FIFOs)**:
[PR #335](https://github.com/open-logic/open-logic/pull/335) `rustyqt:feature/olo_ft_fifo_sync_packet`
(worktree `D:/git/open-logic-syncfifo`) -> upstream `feature/fault-tolerant`, 4 commits on `c5b55fc`:
`136a969` (TEST: shared pkg + ftPushBeat/ftExpectBeat/ftExpectedBeat), `9d21f30` (FEATURE: fifo_sync),
`d786e36` (FEATURE: fifo_packet), `feae171` (FEATURE: integration olo_ft.py/ft.yml/EntityList/
compile_order/olo_ft_dev.core). NEW vs backlog: architecture diagrams for both FIFOs
(`doc/ft/fifo/*_arch.drawio.png`, sdp-style; packet shows the 4-entity structure with the
combinational decoder as a floating side-path over the fifo->pl_stage row) — back-applied to the
backlog as `b3eee4a` (pushed); all shared files byte-identical between branches. PR body presents
the DROP_ONLY elaboration-gate deviation, the `SmallRamStyle_g="registers"` default, and asks the
`MaxPacketSize_g`/`Optimization_g` parity question. Verified: GHDL **6048/6048** on the PR branch,
vsg 3.27 = 0 (5 VHDL files), markdownlint = 0. Design note (user-explored, decided): keep comb
decode + bundled pl_stage over a parallel pipelined-decoder/fork-join variant — alignment of
data/Last/Size is structural (single control), no SEU desync failure mode; externally identical, so
distributed decode remains a possible later internal IMPROVEMENT. Next in queue after #335: CDC PR,
then async FIFO. Also on the backlog: async-FIFO architecture diagram added
(`doc/ft/fifo/olo_ft_fifo_async_arch.drawio.png`, commit `4f9df2c`, pushed) — 7-block peer
structure (core center, RAM above, 2x cc_bits below, cc_reset bottom, codecs at the sides), rides
with the future async PR._

_Update 2026-08-06 (b) — **Roadmap comment POSTED on #320**
([#issuecomment-5203028242](https://github.com/open-logic/open-logic/pull/320#issuecomment-5203028242)):
announces the sync-FIFO PR next (`olo_ft_fifo_sync` + `olo_ft_fifo_packet`), defers the async FIFO
behind a separate `olo_ft_cc_*` PR (two-PR split), reveals the full queue to the maintainer for the
first time (delays, AXI masters incl. the `RamStyle_g` base prereq, safe-FSM cleanup, cam/fix-filter
candidates), and asks him to merge `main`/`develop` into `feature/fault-tolerant` to limit drift.
Deliberately NOT mentioned (belongs in the FIFO PR description): the packet FIFO's DROP_ONLY
rejection and the `Optimization_g`/`MaxPacketSize_g` parity question. Next action: stage the
sync-FIFO PR (worktree off `upstream/feature/fault-tolerant` at `c5b55fc`)._

_Update 2026-08-06 — **PR #320 MERGED 2026-07-31** by obruendl as `c5b55fc` into
`upstream/feature/fault-tolerant` (no fifth review round; the 2026-07-29 fixes were accepted as-is).
All four ft PRs so far are merged: #294 (sp RAM + codec), #316 (sdp), #319 (tdp), #320 (scrubbers).
Maintainer's closing comment: "I think now only the FIFOs are missing, right? And they should be
trivial thanks to the ECC encoder / decode entities." — he expects **FIFOs next** and does not know
about the CDC set, delays, AXI masters or safe-FSM work. Sequencing note for the next staging: the
sync FIFO has no CDC dependency, but `olo_ft_fifo_async` instantiates the `olo_ft_cc_*` entities, so
either the CDC PR goes first or the FIFO PR is split sync-first. The fork staging branch
(`origin/feature/fault-tolerant`, tip `75ec27f`) is historical; per-feature PR branches (like
`feature/olo_ft_ram_scrubber` for #320) are cut from `upstream/feature/fault-tolerant`. Backlog
(`3ff8dc5`) is already byte-identical to the merged scrubber content per the 2026-07-30 entry. The
former OPEN item "maintainer coverage re-check + multi-simulator run" is resolved by the merge; the
local Libero inference run for the ft.yml `sdp_scrub` change stays open (low priority now)._

_Update 2026-07-30 — **Backlog merged with upstream 4.6.0 AND the PR #320 round back-applied; both
branches pushed.** (a) **Merge** `main` (release 4.6.0, `ecca8af`) into
`feature/fault-tolerant-all-entities` as `e4c4567`: 9 conflicts, all resolved — the 6 fix-area
files + `olo_fix_mix_c2r.md` took main's side (the backlog only carried older develop copies of the
same upstream PRs #303-#314), `sim/run.py` took main's side for the vopt hunk (**upstream #332
REVERTED the Questa three-step flow**: `-O0`, "does not work on AWS" — so `--modelsim` on the
backlog no longer needs `vopt`, while the PR #320 branch still carries #299's `+acc`/three_step_flow
and therefore still needs QuestaSim_Pro), `doc/EntityList.md` kept the full ft section after main's
new fix rows (`olo_fix_coef_storage`), `compile_order.txt` regenerated. Verified: ft integration in
run.py preserved, `UpdateCoreFiles.py` `ft -> [base, axi]` intact, `olo_base_fifo_async` private-core
restructure intact, `synthesis.yml` ft step survived upstream's action bumps. Regression **6692/6692**
(was 6541; upstream's new fix entities add tests). (b) **PR #320 round back-applied** as 4 commits
`a2579cc..3ff8dc5`: default removal + EntityList section cherry-picked (one EntityList conflict:
the section must land after the backlog's larger ft section), **package move redone by hand** because
the backlog package has 9 procedures (3 extra: `ftPushBeat`/`ftExpectBeat`/`ftExpectedBeat` for the
FIFO TBs, restyled to camelCase with `Inject_v`/`ExpData_v`/`Codeword_v`-style variables) and **10 TB
call-site users** instead of 3, then the TB split cherry-picked cleanly. All 10 scrubber files are
**byte-identical** between backlog and PR branch (verified per file). Verified: regression
**6692/6692**, vsg 3.27 = 0 on all 15 changed VHDL files, markdownlint = 0, `compile_order.txt`
regenerates identical. Also: upstream now ships a `.claude/skills/olo-fix-new-entity` skill in-repo.
**OPEN:** local Libero inference run for the ft.yml `sdp_scrub` change (no CI check on PR #320
exercises ft.yml), and the maintainer's coverage re-check + multi-simulator run on #320._

_Update 2026-07-29 — **PR #320 fourth review round (2026-07-27, "Almost there. Only a few quite
minor things") ANSWERED: 4 commits pushed (`a9b5751..dc91908`), all 4 thread replies + summary
comment posted.** The items: (1) **`ScrubClkHz_g` default removed** (`221ce1c`) — src trio + doc
Default cells `-`; generic now mandatory even free-running; wrapper TBs and the ft.yml sdp_scrub
config set it explicitly. NOTE: no CI check on this PR exercises ft.yml (check-synthesis-config in
`hdl_check.yml` runs only base/axi/intf/fix `--dry-run`; `synthesis.yml` triggers only toward
main) — a local Libero inference run for the ft.yml change is still OPEN. (2) **EntityList
"Private Entities" subsection** linking the scrubber doc (`7f15341`). (3) **`olo_test_ft_pkg`
moved `test/tb` → `test/ft/shared/`** (`714bf49`); outside the VC lint overlay the normal vsg
rules apply → procedures restyled camelCase (`ftWrite`/`ftPreloadFlip`/`ftWriteFlip`/`ftCheckEcc`/
`ftWaitPasses`/`ftCountOverPasses`), variables `PassCnt_v`/`WatchedCnt_v`, PascalCase signal
formals; 3 call-site TBs updated. (4) **Unit TB split** into `olo_ft_private_scrubber_tb` (11
free-running cases) + `olo_ft_private_scrubber_paced_tb` (4 paced cases), both
`run_all_in_same_sim` with TB-level configs (`dc91908`) — VUnit hard-rejects per-test configs
under the attribute; 78 runs kept, 9 simulator invocations (was 78); the behavioral RAM model is
wiped in a per-case preamble (model state persists across cases in one sim). The maintainer's
`IsSynth_c` proposal was **declined in-thread** (would be the library's first functional
translate_off — all 23 existing uses guard asserts/reports; a sim-side base tick alone shortens
nothing since `DivRatio_c` compensates; the TB is already fast via a small `ScrubClkHz_g`);
offered as a separate PR if wanted. Verified: GHDL **5924/5924**, vsg 3.27 = 0, markdownlint = 0,
Questa 419/419 on all scrub TBs. Toolchain: `ModelSim_Pro\win32acoem` NO LONGER works for
`run.py --modelsim` (upstream #299 three_step_flow needs `vopt.exe`, absent in the OEM edition;
symptom: every TB "skips" with `Bad flag from vopt_extra_args?`) — use `QuestaSim_Pro\win64`
(SKILL.md's ModelSim section is outdated). **OPEN:** back-apply this round to the backlog (the
shared pkg has 10 TB users there + backlog ft.yml/wrapper TBs/unit-TB split), local Libero
inference for ft.yml, then the maintainer re-checks coverage and runs all simulators._

_Update 2026-07-07 — **NEW ENTITIES: olo_ft_axi_master_simple + olo_ft_axi_master_full** (4 commits
`88982b6..ab1201a`, pushed; PR-ready). **Composition-wrapper approach** (chosen over ~2900 lines of
verbatim duplication or another stable-entity core extraction): bulk data buffering in external
`olo_ft_fifo_sync` instances with sidebands inside the codeword ({Be,Data} wr / {Last,Data} rd on
simple; {Data} / {Last,Data} on full), wrapped base master at `2*AxiMaxBeats_g` internal depth with
`IntFifoRamStyle_g="registers"` (all 5 internal FIFOs → FFs → vendor-TMR-coverable; FF cost scales
with AxiMaxBeats_g — documented). Works because the base masters' user-side data interfaces are
plain valid/ready streams and the high/low-latency gating uses the INTERNAL fifo level (verified:
LongTransfer TB case streams 40 beats through 16-beat bursts). **Prereq base change committed
separately (`88982b6`, upstreamable standalone): `RamStyle_g` on both base masters.** Wr flags =
countable one-cycle pulses (gated with the internal handshake); Rd flags = data-aligned. Full-master
gotchas encoded in the TB: sizes in BYTES; data-before-command now allowed (improvement, buffer
decouples). **FuseSoC: ft now depends on axi** — `UpdateCoreFiles.py` ft -> [base, axi], ft dev core
references the axi core. TBs reuse `olo_test_axi_slave_vc`. Verified: 108/108 AXI-master tests, full
regression **6541/6541**, vsg 3.27 + markdownlint 0. Remaining ft-coverage candidates: olo_base_cam
(real design work), crc_check DROP mode (compositional), cic/mov_avg/latency_comp (thin once
needed)._

_Update 2026-07-06 (round 3) — **NEW ENTITIES: olo_ft_delay + olo_ft_delay_cfg** (4 commits
`1b9e25f..d5a5a27`, pushed; PR-ready, queue as a future PR after the FIFOs). Codec-sandwich around
`olo_base_delay`/`olo_base_delay_cfg` at codeword width — key insight: **every storage tap (SRL/
MLAB/BRAM/output register) holds a full codeword, so protection is storage-medium independent**
(full `Resource_g` surface kept; the ft answer for LUT-SRL/MLAB dynamic state that vendor TMR
can't cover). Locked ft API (latched ErrInj pair, Out_EccSec/Ded). `EccPipeline_g` 0..1 = one
In_Valid-gated register on the decoded outputs with internal sample compensation (base runs at
Delay-1; cfg does it dynamically, Delay=0 bypass combinational for SupportZero_g). **ft addition
on cfg: `RstState_g` (default true)** — samples-since-reset counter gates data+flags to zero while
the configured delay reaches into never-written storage (kills spurious SEC/DED after reset AND
delay-increase-beyond-history; base_cfg has no reset state at all). Shared `ft_expected_beat`
added to olo_test_ft_pkg. TBs: sample-indexed model (out after edge j = in(j-(D-1)), verified for
SRL/BRAM/single/wire paths), gapped-valid hold checks, injection sweeps, delay-change settle
windows (5-sample base contract). Verified: 194/194 delay tests, full regression **6433/6433**,
vsg 3.27 + markdownlint 0. NOT yet in a staging PR. Next ft-coverage candidates (from the
2026-07-06 RAM-usage audit): axi_master data path, olo_base_cam (needs real design work);
crc_check DROP mode = compositional (FLAG mode + olo_ft_fifo_packet)._

_Update 2026-07-06 (round 2) — **olo_ft_fifo_packet FT-storage enforcement** (`621a09a`, pushed):
`FeatureSet_g=DROP_ONLY` is now REJECTED by an elaboration assert (base stores In_Last of every word
inside the main RAM outside the ECC parity — silent packet split/merge + accounting desync;
violates the no-unprotected-RAM-state rule). `DROP_SKIP_ONLY` stays allowed (main RAM = pure
codeword, like FULL). `SmallRamStyle_g` default flipped `"auto"` → `"registers"` so the
packet-boundary FIFO (end addresses → Out_Last/Out_Size/Out_Next) lands in FFs coverable by vendor
TMR; doc gained a "Fault-Tolerant Storage of Packet Boundaries" section (incl. per-tool note:
Intel uses "logic", verify the synthesis report). Assert verified reproduce-first (temporary
DROP_ONLY config fails elaboration). Test sweep now FULL/DROP_SKIP_ONLY. Full regression
**6239/6239**, vsg + markdownlint clean. **Raise in the PR 8 description**: this is a deliberate
deviation from the base entity's feature set. Interface-parity note for PR 8: the ft wrapper does
not expose `Optimization_g` (always SPEED) or `MaxPacketSize_g` — THROUGHPUT mode is
DROP_ONLY/DROP_SKIP_ONLY-only upstream; decide with the maintainer whether to expose them._

_Update 2026-07-06 — **Backlog modules for PRs 6-10 aligned to the PR #319/#320 review standards**
(12 commits `234963d..cbe38a5` on `feature/fault-tolerant-all-entities`, pushed; the previously
pending 8 scrubber back-apply commits were pushed the same day). Derived the generalizable review
lessons from all 50 maintainer comments on #320 (+ the #319 post-merge fixes) and applied them
module-by-module: (1) **CDC group (PR 9)** — cc_bits/cc_pulse headers trimmed to short-description+
doc-link (topology/timing detail lives in the MD), badges added to all three cc docs, Description
sections reduced to WHAT, stale cross-refs fixed (fifo_async uses olo_ft_cc_bits, cc_pulse crosses
resets via olo_ft_cc_reset, level-signal advice → olo_ft_cc_bits), NEW `doc/ft/olo_ft_pkg_attribute.md`
(base-pkg precedent) + linked EntityList row, cc_pulse TB gained base-parity reset cases
(Reset/NoPulse-RstIn/NoPulse-RstOut) + PulseDuringReset (SR-latch priority). (2) **Shared TB helpers**
— `ft_push_beat`/`ft_expect_beat` (defaulted `last` parameter serves sync/async/packet) added to
`olo_test_ft_pkg`, the triplicated pushBeat/expectBeat removed from all three FIFO TBs (the #320 DRY
comment). (3) **fifo_sync (PR 6)** — doc rebuilt to reviewed structure (badges, interface subsections,
previously MISSING In_ErrInj_Valid row, Architecture section, principles refs); TB: shared helpers,
ResetInFlight, EccPipeline swept 0..2; ASCII arrows in comments. (4) **fifo_async (PR 7)** — doc had
stale SAFETY-RELEVANT claims fixed: CDC section now describes the olo_ft_cc_bits/olo_ft_cc_reset
implementation (old text claimed plain cc_bits + vendor TMR suffices), scrubbing recommendation now
points at the _scrub wrappers (old text referenced a non-existent `Scrub_g` generic); em-dashes
removed; TB to parity (Mixed/FullEmpty/LatchedInjection) + async ResetInFlight (In_Rst only — proves
the reset crossing clears the Out side). (5) **fifo_packet (PR 8)** — doc rebuilt (constraints:
framing/size sidebands not ECC-protected; **Out_Next/Out_Repeat are sampled on the internal FIFO
handshake which runs ahead of the observed output when EccPipeline_g>0** — found while writing the
Repeat TB case, which is therefore EccPipeline_g=0-only); TB: shared helpers, Drop (level-held, both
feature sets), Repeat, ResetInFlight; TB generic + sweep widened to 0..2. (6) **safe-FSM (PR 10)** —
audit-only: commit `7adba0b` already matches the reviewed FSM standard (coverage pragmas, safe-state
recovery), all 11 files vsg-3.27-clean; the two remaining `when others => null` in olo_fix_cordic_vect
are output muxes (not FSMs), correctly untouched; ready to cherry-pick as-is. Verified: full GHDL
regression **6239/6239** (was 6129 — new cases/configs), vsg 3.27 clean on all changed files,
markdownlint clean. PR #320: no new maintainer round since the 2026-07-03 replies._

_Update 2026-07-02 — **PR #320 review round of 2026-06-23 answered in the working tree, LOCAL ONLY —
NOT committed, NOT pushed, NO PR replies posted; user reviews first.** Worktree
`D:/git/open-logic-scrubber` @ `493609a` + uncommitted changes. Maintainer raised 13 inline
comments + 1 general (coverage screenshot). Decisions taken (user-approved): adopt the maintainer's
opportunistic FSM; keep `Scrub_Enable` (EDAC-self-test + external-pacing justification); consolidate
pacer TBs into a new scrubber unit TB. Implemented: (1) **FSM rework** in `olo_ft_private_scrubber`
— collision-only inhibit (user write to scrub addr), reads fill free read-port cycles, `Decide_s`
waits for a free write slot, decoder-response capture **qualified with the scrub read-return pulse**
(fixes a payload-clobber bug in the maintainer's sketch; test `WritebackDataStableDuringWait`), and
the `Idle_s` arm check uses `v.ScrubActive` (a `r.`-check leaked one op per paced pass boundary).
(2) **Overrun bug fixed reproduce-first**: `PacedEnableDropNoOverrun` failed on old RTL (overrun
fired EVERY period while suspended — `ScrubActive` never cleared); suspension now disarms the
watchdog; the untaken `Scrub_Enable='1'`-false branch in the maintainer's coverage screenshot is
covered. (3) Pacer folded into the two-process record under `Paced_c`; warning moved to `p_seq`
under translate_off (olo_base_crc precedent). (4) Strobe-cascade rationale (ratio cap 214'748'000 ->
~2.1 s max at 100 MHz for a single stage) as comment + `ScrubPeriod_g >= 0.001` assert + doc.
(5) New unit TB `test/ft/olo_ft_private_scrubber/` (behavioral RAM model, per-test VUnit configs, NO
run_all_in_same_sim, integer-ms pacer generic to dodge GHDL's no-real-CLI-generics limit; 15 cases,
78 runs; `PartialTrafficCompletesPass`/`WriteTrafficBlocksWriteback` fail on old RTL = A1 evidence,
log in scratchpad `unit_tb_on_old_rtl.log`). Both wrapper `*_scrub_pacer_tb.vhd` DELETED. (6)
Wrapper TB rework: `UserTrafficStarvesScrubRepair` (maintainer's 0x81/0x80 scenario),
`UserBusyNoCorruption` plants a REAL flip (old mask was all zeros) + persists-then-repaired,
`ScrubEnableSuspends` = the 7-step recipe, `ResetInFlight` sweeps reset alignment,
`WritebackAbortsOnContention` -> `ScrubProceedsUnderPartialTraffic` (old premise inverted by the
FSM); free-run overrun==0 check added; sp TB mirrored. (7) Shared `test/tb/olo_test_ft_pkg.vhd`
(ft_write/ft_write_flip/ft_preload_flip/ft_check_ecc(+latency)/ft_wait_passes/ft_count_over_passes,
lower-case per VC overlay). (8) Docs: scrubber+wrapper semantics rewrite, new Suspension section,
**deferred FSM state diagram (drawio) + 4 wavedrom waveforms delivered** under `doc/ft/ram/`;
`Scrub_Overrun` doc rows fixed (`ScrubPeriod_g`, not ClkHz). (9) `compile_order.txt` regen fixed a
stale ordering (scrubber listed before the strobe entities it instantiates). Verified: full GHDL
regression **5924/5924**, vsg 3.25.0 clean (src + TBs + pkg w/ VC overlay), markdownlint clean.
Gotcha: Questa vcom-1030 rejects range-constrained actuals on `signal` formals (GHDL/NVC accept) —
plant-request signals made plain `natural`. Questa branch coverage: **scrubber 100% branches
(43/43), 100% statements**; wrappers 100% statements (pure wiring). **Fmax grid re-run 2026-07-03**
(12 scrub configs, plain-RAM refs reused): collision compare on NO critical path (all worst paths =
RAM output -> ECC decode; verified in the archived rpts), sdp scrub within ~5% of plain ECC RAM
across the grid, sp lat1/low-ecc shows ~±10% single-run P&R scatter on the unchanged decode path
(prev run had scrub FASTER than plain there = noise); numbers + takeaways in the inference-test
skill's `fmax-results/post-opportunistic-fsm/combined-fmax-grid.md`. User hand-edited the FSM
diagram (code-identifier labels, circular self-loops) and had the `scrub reads` lane removed from
the paced-pass waveform. **PUSHED 2026-07-03**: 6 commits `493609a..8738df6` on
`feature/olo_ft_ram_scrubber` (pkg 0abc9b8, FSM rework c000a21, unit TB 222252f, wrapper TBs
be137a6, docs 245dafd, compile_order 8738df6), final pre-commit regression 5924/5924. **All replies
POSTED**: 12 inline thread replies (3518011473..3518014240) + the unit-TB/coverage answer
(4873440138) + the summary comment (4873440742). Awaiting the maintainer's next round.
**Back-applied to the backlog 2026-07-03**: 5 commits cherry-picked onto
`feature/fault-tolerant-all-entities` (`63b364f..6ae5b43`; the PR's compile_order commit was NOT
needed — the backlog's file was already correctly ordered). One hand-merge in
`sim/test_configs/olo_ft.py` (backlog has extra ft entities and a different section order: pacer
sections removed, unit-TB block inserted after ecc_decode). Backlog regression **6129/6129** green.
**CI lint fix 2026-07-03**: the PR's HDL-Check linting job failed with ONE violation
(`olo_ft_private_scrubber.vhd` process_400) — root cause was a vsg version skew: CI pins **3.27**
(`.github/workflows/requirements.txt`), local had the previously-pinned 3.25.0 which reported clean;
3.27 splits process_400 alignment groups at comment lines, so the `r.ValidPipe <=` reset assignment
below its comments must not carry the group padding. Local vsg upgraded to 3.27 (keep it matching
the CI pin), fix committed as `a9b5751` (pushed, `8738df6..a9b5751`) and cherry-picked to the
backlog as `67ad9c0`. Backlog now 8 commits ahead of origin (incl. the 2 older unpushed ones,
8600517 + eaa8e96) — push pending user command._

_Last updated: 2026-06-10 — **PR #320 second review round pushed** (`4f10ff3..4584124`, 7 commits;
maintainer comment posted, body updated). Engine renamed `olo_ft_ram_scrubber` ->
`olo_ft_private_scrubber` (wildcard `olo_ft_private_*` exclude, diagrams relabeled); `Rst` mandatory
+ `Depth_g >= 2` on the scrub wrappers; doc accuracy fixes (popcount worst-case scoped per
principles doc, qualify-with-RdValid rows, starvation advice, abort qualifier, no-tdp rationale,
sp/sdp cross-refs); mutation-verified `UserWriteToInFlightScrubAddr` RMW-race test + TB hardening
(341 scrub instances); FuseSoC ft integration (dev core + `UpdateCoreFiles.py` `ft -> base`; stable
core deliberately deferred to release-time regeneration) + `synthesis.yml` ft inference step.
Verified: PR branch full GHDL regression 5846/5846, vsg 0, markdownlint 0, compile_order
regenerates byte-identical. **All back-applied to the backlog** (`4d5e706..5dcdb5d`, incl.
backlog-only `olo_ft_dev.core` extension to the full ft set), backlog regression green, pushed.
Note: pushing `.github/workflows/*` needs the gh `workflow` OAuth scope (refreshed 2026-06-10)._

_Update 2026-06-15 — **PR #320 follow-up `4de9672` pushed** (`4584124..4de9672` on
`feature/olo_ft_ram_scrubber`): the scrub-wrapper user enables (`WrEna`/`RdEna` on sp,
`Wr_Ena`/`Rd_Ena` on sdp) are now **mandatory** — removed the inherited base-RAM `:= '1'` default,
which floats an unconnected enable high and silently starves the scrubber (holds
`Scrub_Inhibit = User_Wr_Ena ∨ User_Rd_Ena ∨ ¬Scrub_Enable` permanently asserted). Docs `Default`
column `'1'` -> `-`. Authored on the backlog (`cb508d8`, full regression 6051/6051) and cherry-picked
onto the PR branch (worktree `D:/git/open-logic-scrubber`); PR-branch regression 5846/5846, vsg 0,
markdownlint 0. Maintainer comment posted tagging @obruendl. Plain `olo_ft_ram_sp`/`sdp` untouched
(no scrubber → `'1'` default is correct there)._

_Update 2026-06-15 — **PR #320 timing fix `b572f59` pushed** (`4de9672..b572f59` on
`feature/olo_ft_ram_scrubber`; backlog `a1f0713`, `cb508d8..a1f0713`). Registers the scrubber
writeback (`EccSecReg`/`EccDedReg`/`WbData`) and acts in `Decide_s` one cycle later, splitting the
`RAM→decode→re-encode→RAM` combinational loop addressed by reviewer comment 3408663111. **Libero STA
(register-ring harness, MPFS250T, W32/D256):** `olo_ft_ram_sdp_scrub` `EccPipeline_g=0`/
`RamRdLatency_g=1` **124.5 → 174.4 MHz**, now at parity with `olo_ft_ram_sdp` (172.8); residual
scrubber cost across the EccPipeline×RamRdLatency grid ≤9% (port-arbitration muxes, not a loop);
`RamRdLatency_g=2` lifts the scrubber to 248–273 MHz. Abort-without-advance guarantee unchanged;
`ScrubEnablePreservesAddr` TB timing model updated (+1 cycle/op). Full GHDL regression green, vsg 0.
**Encoder pipeline (`EccEncPipe_g`) evaluated and declined** — encode is shallower than decode, never
the sync limiter. Address-mux (comment 3408674095) never on the critical path. Fmax tooling persisted
in the `open-logic-inference-test` skill (`OLO_TIMING_REGS=1`); pre/post grids saved under that skill's
`fmax-results/`. "In-depth Fmax analysis" comment posted on the PR._

_Update 2026-06-16 — **PR #320 review-response batch: 10 commits on `feature/olo_ft_ram_scrubber`
(`b572f59..473ccf2`), LOCAL ONLY — NOT pushed, NO PR comments posted; user reviews the series before
push.** Worktree `D:/git/open-logic-scrubber`. Responds to @obruendl's review round. Commits:_

1. `4982776` IMPROVEMENT: **Minimal scrubber status interface** — `Scrub_EccSec`/`Scrub_EccDed` gated
   internally into clean directly-countable one-cycle pulses; **`Scrub_Rd_Valid` removed**,
   `Scrub_Rd_EccSec`/`Scrub_Rd_EccDed` -> `Scrub_EccSec`/`Scrub_EccDed`. Supersedes the `Scrub_Rd_*`
   surface in "Scrubbing concept" below. TBs rely on indirect observability.
2. `bfb1675` IMPROVEMENT: **Opt-in internal pacer + `Scrub_Overrun`** in `olo_ft_private_scrubber` —
   `olo_base_strobe_gen` (1 kHz) -> `olo_base_strobe_div` cascade; generics `ScrubClkHz_g`/
   `ScrubPeriod_g` (default `0.0` = free-running), `ScrubActive` gate, `Scrub_Overrun` watchdog +
   sim warning + elaboration asserts; both wrappers pass through. Dedicated `*_scrub_pacer_tb` (the
   pacer changes the activity pattern so it can't live in the functional TB; GHDL can't override
   `real` generics from the CLI, so the pacer TBs default the pacer ON and sweep `RamRdLatency_g`).
3. `5327de6` IMPROVEMENT: `WaitCnt` -> un-reset bounded `natural`.
4. `96e88c7` DOC: trim the verbose Description headers on the 3 scrub sources.
5. `fc8a4d1` TEST: pacer CI synthesis coverage — `olo_ft_ram_sp_scrub` ft.yml config flipped
   pacer-ON (synthesizes the strobe cascade); `sdp_scrub` stays pacer-off. (The planned "olo_ft_pkg_ecc
   use-clause + in_reduce CI gap" turned out a non-issue — `in_reduce` already present; top.template
   doesn't need the import because every codeword-width port is reduced.)
6. `479c7e0` DOC: rework the 3 scrub doc pages — minimal status interface, pacer, corrected
   registered-FSM timing (response registered, `Decide_s` at T+L+1), de-dup wrappers -> engine.
7. `041d208` TEST: factor TB pass-counting boilerplate -> `waitPasses()` / `countOverPasses()`.
8. `ff133a7` IMPROVEMENT: **move the single-port address mux INTO `olo_ft_private_scrubber`** behind
   a `SinglePortRam_g` generic (default false) + new `Ram_Addr` output. `sp_scrub` sets it true
   (own mux removed, consumes `Ram_Addr`); `sdp_scrub` leaves `Ram_Addr` open. Answers obruendl's
   "offer an address pipeline option" comment (gives it a home; data says it's not needed).
9. `71c8479` DOC: refresh both architecture diagrams — scrubber drawn as a **U-shape** block
   wrapping the RAM, every port/intermediate signal as its own arrow, current interface; editable
   PNGs updated in place (embedded source). Bundled with the user's wrapper port-comment trims.
10. `473ccf2` DOC: restore the diagram image references in the two wrapper doc pages.

_Verification (PR branch `473ccf2`): full GHDL regression **5858/5858**, scrub regression 353/353
(341 functional + 12 pacer), vsg 0, markdownlint 0. Libero STA (register-ring harness, MPFS250T,
W32/D256) post-feature: `sp_scrub` paced 2 BRAM / 438 LUT / 409 SLE, `sdp_scrub` 1 BRAM / 240 LUT /
203 SLE — synthesizes cleanly._

_**Fmax extension** (saved under the `open-logic-inference-test` skill `fmax-results/post-fsm-fix-sp/`,
NOT git): added `olo_base_ram_sp` (281 MHz @ lat1, 263 @ lat2), `olo_ft_ram_sp` and
`olo_ft_ram_sp_scrub` across the EccPipeline x RamRdLatency grid. **Answer to obruendl's address-mux
timing question: the mux is NOT the limiter** — `olo_ft_ram_sp_scrub` (has the collapse mux) vs
`olo_ft_ram_sdp_scrub` (1:1, no mux) differ only within ~±6% and non-systematically (P&R noise); the
ECC **decode** dominates (plain RAM 281 -> ECC 157-213 MHz @ lat1). A reply comment comparing
sp_scrub vs sdp_scrub is **drafted but NOT posted** (awaiting user go-ahead)._

_**Open / next steps:** (a) user reviews the 10-commit series, then push to PR #320; (b) post the
drafted obruendl Fmax reply; (c) **back-apply this batch to the backlog** `feature/fault-tolerant-all-entities`
(backlog still has the pre-batch `Scrub_Rd_*` interface, wrapper-side mux, no pacer); (d) the
"Scrubbing concept" and "Cross-cutting API decisions §4" sections below describe the OLD `Scrub_Rd_*`
status surface — superseded by the minimal `Scrub_EccSec` / `Scrub_EccDed` / `Scrub_PassDone` /
`Scrub_Overrun` interface._

_Update 2026-06-16 (round 2) — **PR #320 batch PUSHED and the review answered.** Added a 12th commit
`493609a` IMPROVEMENT: enable the pacer via `ScrubPeriod_g > 0.0` (default `0.0` = free-running) instead
of `ScrubClkHz_g`, which now defaults to 100 MHz (plain clock-frequency input); dropped the tautological
`ScrubPeriod_g` assert. (Commit `0e95d69` DOC cleanup of in-line comments/doc duplication preceded it.)
Pushed `b572f59..493609a` to `origin/feature/olo_ft_ram_scrubber`. Verification after the change: full
GHDL regression **5858/5858**, vsg 0, markdownlint 0. **All @obruendl inline comments answered** (35
thread replies) plus a summary PR comment thanking the maintainer
([#issuecomment-4722221202](https://github.com/open-logic/open-logic/pull/320#issuecomment-4722221202)).
Positions taken (open in their threads, not yet resolved by the maintainer): keep the **conservative
FSM** (simplicity, decided), **minimal interface** (no verification-only `Scrub_WordDone`/`Scrub_Addr`),
keep the **`olo_ft_private_scrubber` name** (matches the standalone `olo_fix_private_optional_reg`
precedent). Deferred: the FSM state diagram + sample waveforms (until the FSM discussion closes). **Still
pending: back-apply this whole batch to the backlog** `feature/fault-tolerant-all-entities` (still on the
pre-batch `Scrub_Rd_*` interface, wrapper-side mux, no pacer)._

_Update 2026-06-16 (round 3) — **PR #320 batch back-applied to the backlog**
`feature/fault-tolerant-all-entities`. Two commits on top of `a1f0713`: `8600517` (scrubber
sources/TBs/docs/diagrams overlaid to the reviewed state, incl. the two new `*_scrub_pacer_tb`) and
`eaa8e96` (integration: `olo_ft.py` pacer configs, `ft.yml` pacer-on `sp_scrub` config + `sdp_scrub`
in_reduce, `compile_order.txt` regen for the new scrubber -> strobe_gen/div dependency). The 12 scrubber
files are now byte-identical to the PR branch. Verified on the backlog: full GHDL regression
**6063/6063**, vsg 0, markdownlint 0. `olo_ft_dev.core` / `EntityList.md` needed no change (no new source
entity; scrub rows identical). Done via file overlay rather than cherry-pick because the backlog had
already applied the earlier round (rename, Rst, enables, registered writeback) as its own commits, so the
12 batch commits would double-apply/conflict. NOT pushed (back-apply only)._

**Staging-workflow refinement (PR 3):** because the backlog had uncommitted scrubber work, the PR was
built in an **isolated `git worktree`** (`git worktree add ../open-logic-tdp -b feature/olo-ft-ram-tdp
upstream/feature/fault-tolerant`) so the backlog was never touched. A fresh worktree does NOT init
submodules, so `python sim/run.py --compile_list` failed on `en_cl_fix_pkg` until
`git submodule update --init 3rdParty/en_cl_fix` was run in the worktree. After PR push, removed with
`git worktree remove --force`. Use this pattern whenever the backlog has uncommitted work.

## Backlog state (`feature/fault-tolerant-all-entities`)

Every ft entity is implemented, committed, and green. The full GHDL regression passes
(**6810 / 6810**, `python sim/run.py -p 16`). After the #315 rebase the branch sits as a linear
series on top of `develop`+#315 (the SHAs below are pre-rebase — reconcile against `git log`):

| Commit | Type | Scope |
| --- | --- | --- |
| ~~`a2ba457`~~ | TEMPORARY | `Rd_Valid` shim on `olo_base_ram_sdp/tdp` — **dropped** in the #315 rebase; superseded by #315 (reconciled by `a7248ba` + `2ccb205`) |
| `e72bd64` | IMPROVEMENT | safe-FSM recovery (`when others =>` safe state) across axi/base/fix/intf |
| `d56e9f1` | FEATURE | TMR CDC primitives `olo_ft_cc_bits/pulse/reset` + `olo_ft_pkg_attribute` |
| ~~`22856ea`~~ | IMPROVEMENT | `FaultTolerant_g` generic on `olo_base_fifo_async` — **superseded** by `78bd68c` (shared private core, see "Async-FIFO layering decision") |
| `621fa4f` | FEATURE | ECC RAMs `olo_ft_ram_sdp` / `olo_ft_ram_tdp` |
| `55914cf` | FEATURE | scrubbing RAMs `olo_ft_ram_sp_scrub` / `olo_ft_ram_sdp_scrub` (+ `olo_ft_ram_scrubber`) |
| `e479d8d` | FEATURE | ECC FIFOs `olo_ft_fifo_sync/async/packet` |
| `e5d827c` | FEATURE | build/test/inference integration (`compile_order.txt`, `olo_ft.py`, `ft.yml`) + `EntityList.md` |
| `78bd68c` | IMPROVEMENT | extract `olo_private_fifo_async_core`; remove base→ft dependency (see "Async-FIFO layering decision") |

Because some commits are coarser than the per-PR plan (one covers `ram_sdp` + `ram_tdp`, one covers
all three FIFOs), porting those PRs means file-level cherry-picks rather than whole-commit picks.

## Maintainer dependency

- **PR [#315](https://github.com/open-logic/open-logic/pull/315)** — adds `RdEna` / `RdValid` to all
  base RAMs. **Merged to `develop`** (`f4fb750`) on 2026-05-29. The backlog was rebased onto
  `develop`+#315: both `TEMPORARY` base-RAM shims were dropped and the ft RAM wrappers now use the
  official interface (sp/sdp/tdp wire `Rst`/`Rd_Rst` into the base RAM; tdp exposes
  `A_RdEna`/`B_RdEna`).
  **Update (2026-06-01):** with #294 merged, upstream `feature/fault-tolerant` now equals `develop`
  + the ft merge commit (`develop` behind by 1, ahead by 0). It contains #315 on both
  `olo_base_ram_sdp` (`Rd_Ena`/`Rd_Valid`) and `olo_base_ram_tdp` (`A_RdEna`/`B_RdEna`), so PRs 2–5
  build on the official base interface upstream. The earlier diff-bloat caveat is resolved.

## Per-PR status

| # | Scope | Backlog source | Status |
| - | ----- | -------------- | ------ |
| 1 | `olo_ft_pkg_ecc` + `olo_ft_ram_sp` | (already on `feature/fault-tolerant`) | **MERGED** — PR #294 merged 2026-06-01 (`87c3688`) |
| 2 | `olo_ft_ram_sdp` | `621fa4f` | **MERGED** — upstream PR [#316](https://github.com/open-logic/open-logic/pull/316) merged 2026-06-04 (`10be850`), approved "All good - no comments". Included `ResetInFlight` TB case + `Rd_Rst` wiring; EccPipeline swept 0..2 |
| 3 | `olo_ft_ram_tdp` | `621fa4f` | **MERGED** — upstream PR [#319](https://github.com/open-logic/open-logic/pull/319) merged 2026-06-05 (squash `5d88e97`). Maintainer folded in his own post-merge fixes (no change request): `RamBehavior_g="WBR"` + `tool_omit: cologne` in ft.yml, added `ft` to gowin/quartus/vivado `import_sources.tcl`, and a top-of-doc Cologne/Yosys WARNING box. **All back-applied to the backlog** (`3cf46fa`, `b991d24`) — see open items |
| 4+5 | `olo_ft_ram_sp_scrub` + `olo_ft_ram_sdp_scrub` (+ shared `olo_ft_ram_scrubber`) | backlog `1afee8b` | **In review** — upstream PR [#320](https://github.com/open-logic/open-logic/pull/320) open (`rustyqt:feature/olo_ft_ram_scrubber` off upstream `5d88e97`, single commit `e966f7e`, 14 files, +2145). sp_scrub + sdp_scrub share the reusable scrubber engine, so one combined PR. **No `tdp_scrub`** (cross-clock-domain out of scope; scrub variants sync-only). ft.yml blocks in upstream in_reduce/out_reduce style. `olo_ft_ram_scrubber` shipped as a documented internal helper, NOT given an EntityList row (mirrors backlog). **Pre-PR review refactor (applied to the branch, NOT yet back to backlog):** moved the user RdValid mask INTO the scrubber engine (new `Ram_Rd_Valid` in / `User_Rd_Valid` out); renamed wrapper RAM taps `Dec_*`->`Ram_*`; scrubber-engine doc FSM diagram removed (words-only); sp/sdp arch diagrams redrawn (mask folded in, RdValid out of scrubber). Verified: full regression 5736/5736, vsg 0, markdownlint 0. **Inference test not run locally** (needs Libero patch dance). Worktree `D:/git/open-logic-scrubber` kept. **Refactor back-applied to the backlog** (`2bbca2b`, 9 files; full regression 5941 green, vsg 0, markdownlint 0) so backlog == PR branch for the scrubber entities. **Multi-agent /review (ultracode) ran on the PR** (recommendation request-changes; RTL correct, findings were coverage/config): fixes applied + pushed to the PR as `07e4a1d` (TEST: ResetInFlight + WritebackAbortsOnContention + ScrubEnablePreservesAddr in both scrub TBs; all three mutation-tested to confirm they catch their targeted regression) and `4f10ff3` (BUGFIX: exclude private `olo_ft_ram_scrubber` from ft.yml inference coverage so `--check-coverage` passes). Same two changes back-applied to the backlog. Full regression green, vsg 0. **Second review round (2026-06-10):** 7 further fix commits pushed (tip `4584124`; engine renamed to `olo_ft_private_scrubber`, Rst mandatory, Depth_g >= 2, doc accuracy, mutation-verified RMW-race test, FuseSoC/CI ft integration — details in the header note); back-applied to backlog (tip `5dcdb5d`); PR body updated and maintainer comment posted tagging @obruendl. **Follow-up 2026-06-15 (`4de9672`, PR tip `4584124..4de9672`):** scrub-wrapper user enables made mandatory (removed the `:= '1'` default that silently starves the scrubber; docs `Default` -> `-`); cherry-picked from backlog `cb508d8`; PR-branch regression 5846/5846, vsg 0, markdownlint 0; comment posted. **Follow-up 2026-06-16 (LOCAL, unpushed): 10-commit batch `b572f59..473ccf2` — minimal status interface (drop `Scrub_Rd_*`), opt-in pacer + `Scrub_Overrun`, `SinglePortRam_g` mux move into the engine, U-shape architecture diagrams; full details + open items in the 2026-06-16 header note. Not pushed, no PR comments posted, not back-applied to backlog.** |
| 6 | `olo_ft_fifo_sync` | `e479d8d` | **In review** — upstream PR [#335](https://github.com/open-logic/open-logic/pull/335) (combined with PR 8). First review round answered; entity simplified to `Pipeline_g=0` codecs, no `EccPipeline_g` (see the 2026-08-27 header note). Back-applied to the backlog as `03cd3f8` |
| 7 | `olo_ft_fifo_async` (+ shared `olo_private_fifo_async_core` in `olo_base_fifo_async`) | `e479d8d` + `78bd68c` + `03cd3f8` | Ready on backlog — pending port (after PR 9). Carries the base-FIFO restructure, not the old `FaultTolerant_g` generic. Also simplified to `Pipeline_g=0`, no `EccPipeline_g` (`03cd3f8`, same read-side status defect as the sync FIFO) |
| 8 | `olo_ft_fifo_packet` | `e479d8d` | **In review** — upstream PR [#335](https://github.com/open-logic/open-logic/pull/335) (combined with PR 6; carries the DROP_ONLY deviation + `MaxPacketSize_g`/`Optimization_g` parity question). Also simplified to `Pipeline_g=0`, no `EccPipeline_g`. Back-applied to the backlog as `03cd3f8` |
| 9 | `olo_ft_pkg_attribute` + `olo_ft_cc_bits/pulse/reset` | `d56e9f1` | Ready on backlog — pending port (prereq for PR 7) |
| 10 | `olo_base_*` safe-FSM recovery cleanup | `e72bd64` | Ready on backlog — independent hardening, port any time |

### Sequencing notes

- **#315 has merged to `develop`**; ft RAMs (PRs 2–5) are already reconciled onto its
  `RdEna`/`RdValid` interface on the backlog.
- **PR 9 (CDC) before PR 7** (`olo_ft_fifo_async` instantiates `olo_ft_cc_bits`/`olo_ft_cc_reset`
  via `FaultTolerant_g`).
- **PR 4 after PR 1** (`olo_ft_ram_sp_scrub` wraps `olo_ft_ram_sp`); **PR 5 after PR 2**.
- PRs 9 (CDC) and 10 (safe-FSM) are independent and can go early.

## Cross-cutting API decisions (locked, applied across the backlog)

Reference for upstream reviewers — why the API of every ECC-protected entity looks the way it does.

1. **Error injection** — paired `ErrInj_BitFlip` (codeword-wide flip pattern,
   `eccCodewordWidth(Width_g)` bits) + `ErrInj_Valid` (latched strobe). The wide port allows
   exercising every codeword bit and arbitrary DED pairs; the latch decouples injection from data
   timing. The `olo_ft_ecc_encode` primitive keeps a direct-apply input; the latch lives in each
   RAM/FIFO wrapper.
2. **Status flags** — output ports renamed to `*EccSec` / `*EccDed` (from `*SecErr` / `*DedErr`) for
   consistency with the `Ecc*` naming. Package functions `eccSecError()` / `eccDedError()` keep
   their names (API identifiers, not ports).
3. **`RamRdLatency_g`** — the RAM read-latency generic is named `RamRdLatency_g` to make clear it
   controls the wrapped `olo_base_ram_*` latency, not end-to-end latency. Total read latency is
   `RamRdLatency_g + EccPipeline_g`.
4. **`RdValid`** — every ECC RAM exposes a `RdValid` (or `Rd_Valid` / `A_RdValid` / `B_RdValid`)
   pulse, the read-enable delayed by `RamRdLatency_g + EccPipeline_g` so it is time-aligned with the
   data path. Scrub variants mask cycles consumed by the scrubber. FIFOs use the wrapped
   `Out_Valid` and need no separate port.

The AXI-S codec architecture (`olo_ft_ecc_encode` / `olo_ft_ecc_decode` as full AXI4-Stream entities
with `In_Valid`/`In_Ready`/`Out_Valid`/`Out_Ready`, `Pipeline_g` capped 0..1 encode / 0..2 decode,
`UseReady_g` to select back-pressure vs register-chain) is already in upstream and the wrappers
compile against it.

## Async-FIFO layering decision (resolved, `78bd68c`)

**Problem.** The first cut of the ft async FIFO (commit `22856ea`) added a `FaultTolerant_g` generic
to the base entity `olo_base_fifo_async`; when `true`, six `generate` blocks swapped the three CDC
primitives (`olo_base_cc_bits`×2 + `olo_base_cc_reset`) for their TMR counterparts
(`olo_ft_cc_bits`×2 + `olo_ft_cc_reset`). That made a **base-area entity instantiate ft-area
entities** — the only `src/base → work.olo_ft_*` reference in the repo. It inverts the intended
layering (ft is the "counterpart above base"; `UpdateCoreFiles.py` encodes base→[], others→base) and
breaks FuseSoC packaging: `olo_base_dev.core` declares no ft dependency, there is no `olo_ft` core,
so a base-only consumer with `FaultTolerant_g=true` fails elaboration (only the single-`olo`-library
sim flow hid it).

**Options weighed.**

- **A — TMR as a generic on `olo_base_cc_bits`/`cc_reset`.** Clean layering, but pushes the TMR
  concept *into* base (base CC learns triplication) — erodes the very boundary the `ft` area exists
  to keep.
- **B — inject the CDC entity from outside.** Infeasible in plain VHDL (no entity-injection generic).
- **C — duplicate the FIFO in ft.** Clean layering but ~270 lines of copied control logic.
- **C′ (chosen)** — extract a private control core, instantiated by both FIFOs. No duplication; TMR
  stays in ft; base stays fault-tolerance-free.
- **D — make `olo_base` depend on an `olo_ft` core.** Circular (ft already depends on base).

**Decision: C′.** Split the FIFO so the CDC flavor is chosen by the *outer* entity:

- `olo_private_fifo_async_core` (inline in `olo_base_fifo_async.vhd`) — **pure control logic** only
  (pointers, Gray coding, level/full/empty flags, the `Optimization_g` SPEED/LATENCY muxes).
  **No RAM, no CDC, no entity instantiations.** The storage RAM and the Gray-pointer + reset
  crossings are exposed as ports (`Ram_Wr_*`/`Ram_Rd_*`, `WrGray_Out`/`In`, `RdGray_Out`/`In`,
  `In_RstSync`/`Out_RstSync`).
- `olo_base_fifo_async` — core + `olo_base_ram_sdp` + plain `olo_base_cc_bits`×2 +
  `olo_base_cc_reset`. **`FaultTolerant_g` generic removed.**
- `olo_ft_fifo_async` — a **peer** (no longer wraps the base FIFO): `olo_ft_ecc_encode` → core (at
  codeword width) + `olo_base_ram_sdp` + `olo_ft_cc_bits`×2 + `olo_ft_cc_reset` → `olo_ft_ecc_decode`.

**Why ECC stays encode-before / decode-after (not just an `olo_ft_ram_sdp` inside the FIFO):** the
codeword is protected end-to-end through the FIFO, including the write-side `DataReg` pipeline
register — using an ECC RAM would leave that register holding unprotected plain data (a flip there
becomes a valid-but-wrong codeword). It also keeps the FIFO's read path combinational (no extra
`EccPipeline` latency inside the FIFO); the decoder's own valid pipeline absorbs `EccPipeline_g`
*after* the FIFO. (RAMs are the opposite case — the RAM *is* the storage, no surrounding datapath, so
ECC-in-the-RAM is right there.)

**Result.** `grep work.olo_ft src/base/` → 0; base depends only on base, ft depends on base (core,
RAM) + ft (CDC, ECC) — a clean DAG. Behavior- and interface-preserving (only `FaultTolerant_g`
dropped from the base FIFO). Verified: full regression **5869/0**, vsg + markdownlint clean, two
adversarial reviews (faithful core extraction; wrapper wiring / CDC directions / AXI-S handshake
intact). This modifies a **stable base entity**, so it is a proposal for the maintainer (raise before
the FIFO PR).

## Scrubbing concept — D.13 resolved

Decision: scrubbing is implemented as **separate `olo_ft_ram_*_scrub` wrapper entities** (not a
`Scrubbing_g` generic on the RAM), using **opportunistic** scheduling, with a **private reusable**
scrubber FSM (`olo_ft_private_scrubber`; named `olo_ft_ram_scrubber` until the 2026-06-10 review
round). The scrubber reads each address in idle slots and writes back
SEC-corrected words without stalling the user port; user accesses always win.

Resulting surface:

- Internal FSM: 3 states (`Idle_s`, `ReadWait_s`, `Decide_s`); writeback, address advance and
  `Scrub_PassDone` all fire in `Decide_s`.
- **External control port is `Scrub_Enable`** (active-high, default '1'). The `olo_ft_private_scrubber`
  combines it with user-port-busy into an *internal* `Scrub_Inhibit = User_Wr_Ena ∨ User_Rd_Ena ∨
  ¬Scrub_Enable`; any user activity (or `Scrub_Enable='0'`) aborts an in-flight scrub back to `Idle_s`
  without advancing the address. (Do not call any port `Scrub_Inhibit` — it is an internal signal.)
- **[SUPERSEDED 2026-06-16 — see header note: the `Scrub_Rd_*` surface below was replaced by the
  minimal `Scrub_EccSec` / `Scrub_EccDed` (internally gated, directly countable) / `Scrub_PassDone` /
  `Scrub_Overrun` interface on the PR branch.]** User-facing status outputs carry the `_Rd_` infix:
  `Scrub_Rd_Valid`, `Scrub_Rd_EccSec`, `Scrub_Rd_EccDed`; `Scrub_Rd_EccSec`/`Ded` are codec
  pass-throughs that the consumer qualifies with `Scrub_Rd_Valid`. `Scrub_PassDone` is not tied to a
  specific read.
- The scrubber acts **only when both user ports are idle** (single shared port on sp; on sdp the user
  still gets independent W/R ports but the scrubber is gated by either being active — it does *not*
  run concurrently with a user access). RdValid masking is a combinational `RAM_RdValid ∧ ¬Scrub_Rd_Valid`
  in the wrapper; the length-L read-valid pipeline lives inside the scrubber FSM (no wrapper shift reg).

**Doc/diagram quality (2026-06-03, backlog).** Both scrub docs rewritten to RAM-doc quality (badges,
principles links, accurate interface tables) and corrected for several stale errors the old text had
(wrong `Scrub_Valid`/`Scrub_EccSec` names → `Scrub_Rd_*`; a non-existent sticky `Collision` flag; a
bogus wrapper-side RdValid shift register; an sdp "concurrent with user write" claim; broken links/
anchors). Added drawio architecture diagrams `olo_ft_ram_sp_scrub_arch` / `olo_ft_ram_sdp_scrub_arch`
and an FSM state diagram in the new `doc/ft/olo_ft_ram_scrubber.md` (resolves the previously-broken
`olo_ft_ram_scrubber.md` link). Scrub TBs widened to `EccPipeline_g` 0..2 (swept 0/1/2) for parity
with the entity range. Verified: scrub regression green, vsg + markdownlint clean, adversarial RTL
cross-check PASS. **Committed 2026-06-05 (`1afee8b`).**

**Scrubber arbitration refactor (2026-06-03, backlog).** Moved the user/scrubber mux *into*
`olo_ft_ram_scrubber` (was duplicated in each wrapper). The scrubber now presents a reusable
**write-channel + read-channel** interface: user side `User_Wr_*`/`User_Rd_*` in, RAM side
`Ram_Wr_*`/`Ram_Rd_*` out (muxed, user-wins), plus decoded-read in and status out. `Scrub_Enable` is
now a scrubber port; `Scrub_Inhibit` and the old `Scrub_Rd_Ena`/`Scrub_Wr_Ena`/`Scrub_Addr`/
`Scrub_Wr_Data` outputs are internal. Result: `olo_ft_ram_sdp_scrub` wrapper is pure-structural (0 mux
lines, channels map 1:1); `olo_ft_ram_sp_scrub` keeps **one** collapse line
(`Ram_Addr <= Ram_Wr_Addr when Ram_Wr_Ena else Ram_Rd_Addr`) since a single-port RAM can't expose two
channels. Behaviorally identical (scrub 231/231, full ft regression green, vsg clean). Docs + both
block diagrams redrawn (scrubber = "user/scrub arbiter + scrub FSM"; FSM diagram unchanged);
adversarial cross-check PASS. Driven by maintainer/user architectural preference; raise as a design
note when porting the scrub PRs. **Committed 2026-06-05 (`1afee8b`).**

## Open items

- **~~Maintainer's post-#319-merge fixes not on backlog~~** — **RESOLVED (2026-06-06)**: when the
  maintainer merged PR #319 (`5d88e97`) he folded in his own fixes (checked synthesis for all tools).
  Back-applied to `feature/fault-tolerant-all-entities` as `3cf46fa` (IMPROVEMENT: `ft` added to
  gowin/quartus/vivado `import_sources.tcl`; `RamBehavior_g="WBR"` + `tool_omit: cologne` in ft.yml —
  import scripts now byte-identical to upstream) and `b991d24` (DOC: Cologne/Yosys TDP WARNING box,
  "Cologne" spelled right vs the upstream "Gologne" typo). Verified: full GHDL regression green
  (5941/5941, unaffected — non-VHDL changes), markdownlint clean. **Libero inference run for tdp not
  re-done** — low risk (mirrors `5d88e97` exactly; maintainer already validated synthesis across all
  tools). Minor: the upstream doc still has the "Gologne Chip" typo — flag to maintainer if desired.
- **~~Backlog `ft.yml` tdp stale port name~~** — **RESOLVED (2026-06-05, `b52cfd5`)**: fixed
  `A_WrEccBitFlip`/`B_WrEccBitFlip` -> `A_ErrInj_BitFlip`/`B_ErrInj_BitFlip` in the backlog ft.yml. (A
  Libero inference run to confirm has not been done — low risk since names now match the RTL and PR #319.)
- **~~Uncommitted backlog work~~** — **COMMITTED (2026-06-05)** as three clean commits on
  `feature/fault-tolerant-all-entities`: `1afee8b` (IMPROVEMENT: scrubber arbitration refactor +
  scrub docs/diagrams to RAM quality + scrub TBs 0..2), `090c4d9` (TEST: widen sdp/tdp RAM TB
  EccPipeline to 0..2), `b52cfd5` (BUGFIX: ft.yml tdp port name). `olo_ft.py` was split across the
  first two via revert-and-reapply. Backlog working tree is clean.
- **~~PR #294 diff bloat~~** — **RESOLVED (2026-06-01)**: the maintainer synced `develop` into
  `feature/fault-tolerant` around the #294 merge. Upstream `feature/fault-tolerant` is now `develop`
  + the ft merge commit and carries #315; no diff bloat remains. Action carried over: re-sync the
  fork's `origin/feature/fault-tolerant` (`75ec27f`) to upstream `87c3688` before staging PR 2.
- **~~`olo_base_fifo_async` base->ft layering~~** — **RESOLVED** by `78bd68c` (shared private core;
  see "Async-FIFO layering decision"). Base no longer references any ft entity. Still a maintainer
  proposal because it restructures a stable base entity.
- **~~FuseSoC `olo_ft` packaging~~** — **RESOLVED (2026-06-10, PR #320 fix round)**:
  `UpdateCoreFiles.py` gained the `ft` entries (`ft -> base`), `src/ft/olo_ft_dev.core` is generated
  on both branches (PR branch lists the 9 scrubber-PR sources; backlog lists the full ft set). The
  stable `tools/fusesoc/stable/olo_ft.core` is deliberately NOT committed: stable cores pin a
  published release tag (4.5.0 has no `src/ft`) and are only generated by the release-time
  update-files-for-release step (fix-area precedent, PR #140).
- **TB reset coverage gap** — ft RAM testbenches pulse `Rst` only at power-on. **`olo_ft_ram_sdp`
  has a `ResetInFlight` case** (PR #316, and now in the backlog — see next item): asserts reset with
  reads in flight, holds `Rd_Ena` high so a missing reset wiring would leave `Rd_Valid` stuck, checks
  squash + no stale valid + recovery; covers `Rst` (sync) and `Rd_Rst` (async). Key timing detail:
  `Rd_Valid` responds through the `RamRdLatency_g + EccPipeline_g` read-valid pipeline, so flush that
  many cycles before asserting it is low. The case is **sdp-only** — it was never added to `olo_ft_ram_sp`
  (PR #294) or `olo_ft_ram_tdp` (PR #319). Coverage-parity follow-up (NOT a back-apply gap, since the
  backlog matches the merged/PR versions): add an equivalent `ResetInFlight` case to `olo_ft_ram_sp`
  and `olo_ft_ram_tdp` (tdp = per-port `A_`/`B_` reset). Awaiting user go-ahead.
- **~~Backlog `olo_ft_ram_sdp` out of sync with merged PR #316~~** — **RESOLVED (2026-06-05)** on
  `feature/fault-tolerant-all-entities`: the PR #316 refinements never flowed back. Now back-applied as
  `42a1c52` (TEST: `ResetInFlight` case + `Rd_Rst` signal/port wiring, byte-identical to the merged sdp
  TB; targeted GHDL 84/84 incl. all sync+async ResetInFlight configs, vsg 0 violations) and `24b0b9c`
  (DOC: drop the radiation-hardened note the user hand-edited out of the PR, em-dashes -> hyphens;
  markdownlint clean). The scrubber cross-ref paragraph is intentionally kept (scrub entity exists on
  the backlog). RTL needed nothing — only comment trimming differed and the backlog comments are richer.
  Verified sp and tdp have **no** back-apply gap: backlog sp == merged upstream, backlog tdp == PR #319.
- **Doc em-dash style (sp/tdp)** — `doc/ft/olo_ft_ram_sp.md` and `olo_ft_ram_tdp.md` still use em-dashes
  in the principles bullet list, in **both** the backlog and their upstream/PR versions (so it is a
  pre-existing style issue, not a back-apply gap). Violates the no-em-dash doc rule. sp is merged
  upstream (backlog fix would diverge harmlessly); tdp PR #319 is open (could fix the PR branch too,
  which is outward-facing). Awaiting user go-ahead before touching either.
- **AXI master `EccPipeline_g` removal — design decision open.** `olo_ft_axi_master_simple` and
  `olo_ft_axi_master_full` forwarded their own `EccPipeline_g` into their internal `olo_ft_fifo_sync`
  buffers, so `03cd3f8` removed the generic from both (minimal fix; neither master exposes FIFO status,
  so it was a timing knob only). The alternative is to keep the knob by giving each master an internal
  `olo_base_pl_stage` on each ECC buffer output — exactly what the FIFO docs now recommend to users.
  That is new design work, not a back-apply, so it was not started. Both masters are still unported
  (no PR row of their own yet), so there is time to decide. Awaiting user go-ahead.
- Scrubbing question (D.13) resolved (separate `_scrub` entities, above).
