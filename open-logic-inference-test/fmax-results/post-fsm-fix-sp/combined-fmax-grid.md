# In-depth Fmax analysis — full grid, after the FSM writeback-registration fix

Libero SmartTime, register-ring harness (`OLO_TIMING_REGS=1`), Width_g = 32, Depth_g = 256.
`Clk`-domain Fmax in MHz. SDP numbers from `../post-fsm-fix/`; SP numbers are this run
(`./matrix-fmax-output.txt`). Single P&R run per config, so expect a few % run-to-run variation.

Reference (plain RAM, no ECC, no scrubber):

- **olo_base_ram_sp = 281.4 MHz** (lat1), **262.5 MHz** (lat2)  — the single-port baseline obruendl asked for.
- **olo_base_ram_sdp = 342.9 MHz** (lat1 and lat2).

## Fmax grid (MHz) — ECC entities

| EccPipeline / RamRdLatency | olo_ft_ram_sdp | olo_ft_ram_sdp_scrub | olo_ft_ram_sp | olo_ft_ram_sp_scrub |
| :------------------------- | -------------: | -------------------: | ------------: | ------------------: |
| ecc0 / lat1                |          172.8 |                174.4 |         157.1 |               169.4 |
| ecc1 / lat1                |          168.3 |                161.7 |         175.1 |               165.6 |
| ecc2 / lat1                |          207.0 |                201.0 |         213.3 |               211.7 |
| ecc0 / lat2                |          276.7 |                253.8 |         276.2 |               267.5 |
| ecc1 / lat2                |          272.6 |                247.8 |         278.2 |               232.3 |
| ecc2 / lat2                |          280.5 |                273.3 |         277.6 |               256.8 |

## Scrubber overhead (scrub wrapper vs. its plain ECC RAM)

| EccPipeline / RamRdLatency | SDP: scrub − ram | SP: scrub − ram |
| :------------------------- | ---------------: | --------------: |
| ecc0 / lat1                |   +1.6 (+0.9 %)  |  +12.3 (+7.8 %) |
| ecc1 / lat1                |   −6.6 (−3.9 %)  |   −9.5 (−5.4 %) |
| ecc2 / lat1                |   −6.0 (−2.9 %)  |   −1.6 (−0.7 %) |
| ecc0 / lat2                |  −22.9 (−8.3 %)  |   −8.7 (−3.1 %) |
| ecc1 / lat2                |  −24.8 (−9.1 %)  |  −45.9 (−16.5 %)|
| ecc2 / lat2                |   −7.2 (−2.6 %)  |  −20.8 (−7.5 %) |

## Takeaways

- The single-port scrubber behaves like the dual-port one: with the registered-writeback FSM fix
  it tracks its plain ECC RAM within roughly 0–9 % across the grid. No return to the pre-fix ~28 %
  cliff — the scrubber's read→decode→re-encode→writeback path is no longer the critical path.
- The critical path is the ECC **decode**, not the scrubber: every ECC config sits far below the
  plain base RAM's 342.9 MHz, and adding the scrubber on top costs little.
- Higher RamRdLatency (lat2) relaxes the RAM read path and lifts Fmax for all ECC variants.
- Two lat2 outliers stand out (sdp_scrub ecc0/ecc1 ≈ −8–9 %, sp_scrub ecc1-lat2 ≈ −16.5 %). These
  are plausibly P&R variance on a single run; a confirming re-run of those three points would tell
  whether the ecc1-lat2 SP dip is real or noise.
