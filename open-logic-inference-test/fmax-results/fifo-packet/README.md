# olo_ft_fifo_packet - Fmax vs EccPipeline_g

Measured 2026-08-26 on Libero 2025.2, MPFS250T_ES, FCVG484, STD speed, EXT range.
Branch `feature/olo_ft_fifo_sync_packet` @ `feae171` (PR #335 state).
Same harness style as [../fifo-sync](../fifo-sync/README.md): an `olo_base_pl_stage` (Stages_g=1,
UseReady_g=true) on each side of the FIFO. The input stage carries {Drop, Last, Data}, the output
stage carries {EccSec, EccDed, Last, Size, Data}. `Width_g=32`, `Depth_g=256`, `MaxPackets_g=17`,
`FeatureSet_g="FULL"`, `SmallRamStyle_g="registers"` (the ft default).

| EccPipeline_g | Fmax (MHz) | Achieved period (ns) | LUTs | SLEs | Block RAM |
| ------------- | ---------- | -------------------- | ---- | ---- | --------- |
| 0             | 154.9      | 6.46                 | 694  | 610  | 1         |
| 1             | 167.0      | 5.99                 | 696  | 703  | 1         |
| 2             | 176.1      | 5.68                 | 758  | 792  | 1         |

Critical path starts at the block RAM output in all three configurations, as in the sync FIFO.

- `EccPipeline_g=0`: RAM -> decode -> harness output stage (`i_pl_out/.../r.DataMain`).
- `EccPipeline_g=1`: RAM -> decode -> the FIFO's own output stage (`i_fifo/i_pl/.../r.DataShad`).
- `EccPipeline_g=2`: RAM -> decode -> still **stage 0** of the same output stage
  (`i_fifo/i_pl/g_stages.0/.../r.DataMain`).

## Key finding: the second stage does nothing for timing here

In `olo_ft_fifo_packet` the ECC decoder is always combinational (`Pipeline_g => 0`) and
`EccPipeline_g` drives the bundled `olo_base_pl_stage` that carries data plus the Last/Size/Sec/Ded
sidebands. Both stages therefore sit **in series after** the decode, so the decode itself is never
split. The endpoint stays at stage 0 in the report, and the 5.4% gain from ecc1 to ecc2 is placement
noise, not a shorter logic path. It costs one cycle of latency, 62 LUTs and 89 SLEs.

Contrast with `olo_ft_fifo_sync`, where `EccPipeline_g` is forwarded into `olo_ft_ecc_decode` and
stage 2 genuinely splits syndrome from correction:

| EccPipeline_g | sync FIFO | packet FIFO | gap |
| ------------- | --------- | ----------- | --- |
| 0             | 153.2     | 154.9       | -1% |
| 1             | 171.5     | 167.0       | +3% |
| 2             | 226.6     | 176.1       | **+29%** |

So the packet FIFO plateaus around 176 MHz. If it ever has to run faster, the fix is architectural
(pipelining the decoder and aligning the sidebands alongside it), not a larger `EccPipeline_g`.
That trade was discussed and deliberately declined: keeping the decode combinational and bundling
the sidebands through one pipeline makes data/Last/Size alignment structural rather than dependent
on fork/join control state that an SEU could desynchronize.

Resource note: the packet FIFO uses roughly twice the LUTs of the sync FIFO (694 vs 387 at ecc0),
which is the packet-boundary FIFO held in flip-flops (`SmallRamStyle_g="registers"`) plus the packet
control logic.
