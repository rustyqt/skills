# olo_ft_fifo_sync - Fmax vs EccPipeline_g

Measured 2026-08-26 on Libero 2025.2, MPFS250T_ES, FCVG484, STD speed, EXT range.
Branch `feature/olo_ft_fifo_sync_packet` @ `feae171` (PR #335 state).

Harness (`olo_ft_fifo_sync_fmax_wrap.vhd`, temporary, not committed to the repo): an
`olo_base_pl_stage` (Stages_g=1, UseReady_g=true) on the input and on the output side of the FIFO,
so the combinational ECC encode and decode paths are timed register-to-register. The output stage
carries `Out_EccSec` / `Out_EccDed` bundled with the data. Status ports are all connected so the
level and flag logic is not optimized away. `Width_g=32`, `Depth_g=256`, almost-flags enabled.

| EccPipeline_g | Fmax (MHz) | Achieved period (ns) | LUTs | SLEs | Block RAM |
| ------------- | ---------- | -------------------- | ---- | ---- | --------- |
| 0             | 153.2      | 6.53                 | 387  | 361  | 1         |
| 1             | 171.5      | 5.83                 | 376  | 432  | 1         |
| 2             | 226.6      | 4.41                 | 423  | 513  | 1         |

Critical path starts at the block RAM output in **all three** configurations, i.e. the read path
through the ECC decode dominates; the write path (encode) is never critical.

- `EccPipeline_g=0`: RAM -> full syndrome+correction -> the harness output pl_stage
  (`i_pl_out/.../r.DataMain`). The whole decode is combinational between RAM and the first register.
- `EccPipeline_g=1`: RAM -> full syndrome+correction -> decoder output register
  (`i_dec/i_pl2/.../r.DataShad`). Same logic depth, but it now terminates inside the decoder, +12%.
- `EccPipeline_g=2`: RAM -> syndrome -> decoder stage 1 (`i_dec/i_pl1/.../r.DataMain`). The decode is
  split by `Stages1_c` (see olo_ft_ecc_decode.vhd:82-83), which is where the real gain comes from:
  +32% over EccPipeline_g=1 and +48% over 0. Positive slack at 200 MHz.

Takeaway for PR #335: fixing the decoder pipeline to 0 (one of the maintainer's options in the
level-skew thread) costs about a third of the achievable clock (153 vs 227 MHz).
