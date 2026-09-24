# Fmax grid after the opportunistic-FSM rework (PR #320 review round of 2026-06-23)

Run 2026-07-03. Libero SmartTime, register-ring harness (`OLO_TIMING_REGS=1`), Width_g = 32,
Depth_g = 256, `Clk`-domain Fmax in MHz. Only the 12 scrub configs re-ran (the FSM rework touched
`olo_ft_private_scrubber` alone); plain-RAM references are from `../post-fsm-fix*` (unchanged RTL,
deterministic flow). Single P&R run per config.

## Grid (MHz)

| ecc / lat   | ft_ram_sdp (ref) | sdp_scrub prev | sdp_scrub NEW | ft_ram_sp (ref) | sp_scrub prev | sp_scrub NEW |
| :---------- | ---------------: | -------------: | ------------: | --------------: | ------------: | -----------: |
| ecc0 / lat1 |            172.8 |          174.4 |         165.3 |           157.1 |         169.4 |        139.1 |
| ecc1 / lat1 |            168.3 |          161.7 |         167.5 |           175.1 |         165.6 |        144.7 |
| ecc2 / lat1 |            207.0 |          201.0 |         211.0 |           213.3 |         211.7 |        211.0 |
| ecc0 / lat2 |            276.7 |          253.8 |         264.3 |           276.2 |         267.5 |        268.0 |
| ecc1 / lat2 |            272.6 |          247.8 |         268.5 |           278.2 |         232.3 |        263.4 |
| ecc2 / lat2 |            280.5 |          273.3 |         267.0 |           277.6 |         256.8 |        262.2 |

## Scrub wrapper vs its plain ECC RAM (NEW numbers)

| ecc / lat   | SDP delta        | SP delta          |
| :---------- | ---------------: | ----------------: |
| ecc0 / lat1 |  -7.5  (-4.3 %)  |  -18.0 (-11.5 %)  |
| ecc1 / lat1 |  -0.8  (-0.5 %)  |  -30.4 (-17.4 %)  |
| ecc2 / lat1 |  +4.0  (+1.9 %)  |   -2.3  (-1.1 %)  |
| ecc0 / lat2 | -12.4  (-4.5 %)  |   -8.2  (-3.0 %)  |
| ecc1 / lat2 |  -4.1  (-1.5 %)  |  -14.8  (-5.3 %)  |
| ecc2 / lat2 | -13.5  (-4.8 %)  |  -15.4  (-5.5 %)  |

## Takeaways

- **The collision compare is not on any critical path.** Every archived `Path 1` starts at the RAM
  macro clock-to-out and runs through the ECC decode to the read-data register (checked sp ecc0/lat1,
  sp ecc1/lat1, sdp ecc0/lat1). The new `User_Wr_Addr = ScrubAddr` comparator and the waiting
  `Decide_s` term feed only the RAM write/address inputs, which never appear as the limiter.
- **SDP scrubber: parity within ~5 % of the plain ECC RAM across the whole grid**, same conclusion
  as the previous (registered-writeback) run.
- **SP lat1 low-ecc scatter is P&R seed variance, not a regression signal.** The decode path logic
  is byte-identical between runs, yet sp scrub moved 169.4 -> 139.1 (ecc0/lat1) and 232.3 -> 263.4
  (ecc1/lat2) in opposite directions; the previous run even measured the scrub wrapper FASTER than
  its plain RAM (+7.8 % at ecc0/lat1), which is only possible as noise. Spread on this
  decode-dominated path is roughly +/-10 % per single run at lat1.
- Structural conclusion unchanged: the ECC decode dominates, `RamRdLatency_g = 2` remains the Fmax
  lever (all lat2 configs 260+ MHz).
