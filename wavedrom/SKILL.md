---
name: wavedrom
description: Always use when the user asks to create, generate, draw, or design a timing diagram, waveform, signal-level protocol diagram (SPI, I2C, UART, AXI handshake, clock-with-enable, request/acknowledge), bitfield / register-layout diagram, or logic-schematic diagram, or mentions WaveDrom, WaveJSON, wavedrom-cli, `.json5` waveform files, or signal-export to SVG/PNG/PDF.
---

# WaveDrom Diagram Skill

Generate WaveDrom diagrams as WaveJSON (`.json5`) files. Optionally render to SVG, PNG, or PDF via `wavedrom-cli`. WaveDrom covers three variants:

1. **signal** — digital timing waveforms (the most common case)
2. **reg** — bitfield / register-layout diagrams
3. **assign** — logic-schematic (gate-level) diagrams

## How to create a diagram

1. **Pick the variant.** Timing/protocol → `signal`. Register layout → `reg`. Combinational logic → `assign`.
2. **Generate WaveJSON** for the requested diagram. Use JSON5 (unquoted keys, single-quoted strings, trailing commas) — `wavedrom-cli` accepts it directly.
3. **Write the file** to `<name>.json5` in the current working directory.
4. **If the user requested SVG / PNG / PDF**, locate `wavedrom-cli` (see below) and export. If the CLI is not found, keep the `.json5` file and tell the user they can install it with `npm i -g wavedrom-cli`, or paste the WaveJSON into the online editor at https://wavedrom.com/editor.html.
5. **Open the result.** If the open command fails, print the absolute path so the user can open it manually.

## Choosing the output format

| User says | Output |
|-----------|--------|
| (no format mentioned) | `name.json5` only |
| "svg" | `name.json5.svg` |
| "png" | `name.json5.png` |
| "pdf" | `name.json5.pdf` (via Inkscape pipe — see below) |

Examples:
- `/wavedrom create an SPI write transaction` → `spi-write.json5`
- `/wavedrom svg I2C read` → `i2c-read.json5.svg`
- `/wavedrom png AXI handshake` → `axi-handshake.json5.png`

## wavedrom-cli

### Installing

```bash
npm install -g wavedrom-cli   # Node.js v14+ required
```

### Locating the CLI

| Environment | Check |
|-------------|-------|
| Any | `which wavedrom-cli` (or `where wavedrom-cli` on native Windows) |
| Fallback | Check `npm root -g` for `node_modules/wavedrom-cli/bin/cli.js` |

### Export command

```bash
wavedrom-cli -i <input.json5> -s <output.svg>     # SVG
wavedrom-cli -i <input.json5> -p <output.png>     # PNG
```

**PDF** requires piping through Inkscape (no native flag):

```bash
wavedrom-cli -i <input.json5> | inkscape -p --export-filename=<output.pdf>
```

### Opening the result

| Environment | Command |
|-------------|---------|
| macOS | `open <file>` |
| Linux (native) | `xdg-open <file>` |
| WSL2 | `cmd.exe /c start "" "$(wslpath -w <file>)"` |
| Windows | `start <file>` |

## WaveJSON: top-level structure

```json5
{
  signal: [
    // WaveLanes go here
  ],
  head:   { text: 'Title', tick: 0 },         // optional
  foot:   { text: 'Footer' },                 // optional
  edge:   ['a~b time1', 'c-|>d time2'],       // optional
  config: { hscale: 1, skin: 'default' },     // optional
}
```

For **reg** diagrams, replace `signal` with a flat array of field objects (no `signal` key — the top level is the array itself).
For **assign** diagrams, use `{ assign: [...] }` instead of `signal`.

## Variant 1: signal (timing waveforms)

### Synchronous design rules

A timing diagram exists to communicate **when** signals change relative to each other, not just *what* values they take. An incorrect timing diagram is worse than no diagram — it lies about the design. Apply these rules before placing a single waveform character.

1. **Every signal belongs to a clock domain.** Place the clock at the top of the diagram and group signals by their domain. If a signal is in a different domain, draw that clock too and mark the boundary.

2. **Synchronous signals change only on the active clock edge.** For rising-edge designs (the default), a transition between positions N and N+1 in a `wave:` string represents a change *at the rising edge of period N+1*. Never draw a sync signal changing mid-period. One `wave:` character = one clock period; transitions snap to the grid.

3. **Registered outputs lag their inputs by exactly one period.** If `q <= d` on `clk`, then `q` in period N+1 equals `d` in period N. Align the diagram so this one-cycle shift is visually obvious — anything else implies wrong gate-level behavior. The same rule chains: a two-stage pipeline shows a two-period delay, etc.

4. **Combinational outputs change in the same period as their inputs.** A wire that is a combinational function of `q` updates whenever `q` updates — no extra cycle of delay. Inserting a delay implies an extra flop that does not exist in the RTL.

5. **Asynchronous signals are the exception and must be visually marked.** Async resets, pre-synchronizer clock-domain-crossing (CDC) signals, and external inputs may transition mid-period. Separate them from the synchronous group and do not snap their transitions to the clock grid.

6. **Handshake protocols transfer on the cycle where both flags are high.** valid/ready, req/ack, AXI handshake: draw both asserting on a clock edge, the transfer landing on the edge where they overlap, and the deassertion on the following edge. The receiver is allowed to backpressure for any number of cycles — show at least one stall in non-trivial diagrams so this is explicit.

7. **Multi-bit buses change as a unit, on the same edge as their qualifier.** Use `=` (or `2`–`9` for color) plus `data:` with one entry per valid period. The bus value must be aligned with `valid` / `enable` / `cs_n` — never one period off, never updated while the qualifier is low.

8. **Setup and hold are out of scope.** WaveDrom is a register-level view. Setup/hold/metastability/clock skew need an analog-detail tool (TikZ, schematic waveform editor) — do not try to encode them in WaveDrom.

**Self-check before emitting JSON:** for every non-clock signal, name (a) the clock edge that caused each transition and (b) the logic that drove it. If either is unclear, the diagram is wrong — fix it before writing the file.

**Worked example — registered output (`q <= d` on rising edge of `clk`):**

```json5
{ signal: [
  { name: 'clk', wave: 'p.....' },
  { name: 'd',   wave: '0.1.0.', node: '..a.b.' },
  { name: 'q',   wave: '0..1.0', node: '...c.e' },
],
  edge: ['a~>c 1 cycle', 'b~>e 1 cycle'],
}
```

`d` rises at the rising edge of period 2; `q` rises one period later at the rising edge of period 3. Same for the falling transitions at periods 4 and 5. The `~>` edges make the registration delay explicit.

### Wave character reference

| Char | Meaning | Char | Meaning |
|------|---------|------|---------|
| `0` | Low | `1` | High |
| `l` | Low (no transition arrows) | `h` | High (no transition arrows) |
| `L` | Low + marker | `H` | High + marker |
| `x` | Unknown / don't-care | `z` | High-impedance |
| `u` | Rising uncertainty | `d` | Falling uncertainty |
| `p` | Positive-edge clock | `P` | Positive-edge clock + marker |
| `n` | Negative-edge clock | `N` | Negative-edge clock + marker |
| `=` | Data bus (default color) | `2`–`9` | Data bus (colored variants) |
| `.` | Hold previous state one more period | `\|` | Vertical gap / spacer |

Each character occupies one period; `.` extends the prior character.

### Signal entry (WaveLane)

```json5
{
  name:   'clk',           // required
  wave:   'p.......',      // required
  data:   ['A', 'B', 'C'], // optional — labels for `=` / `2-9` cells, in order
  period: 1,               // optional — horizontal scale multiplier (default 1)
  phase:  0,               // optional — horizontal offset in periods
  node:   '.a...b..',      // optional — named anchor points for edges
}
```

### Groups and spacers

A nested array starting with a string makes a **group** with that label. Groups nest arbitrarily. An **empty object** `{}` inserts a vertical gap row.

```json5
{ signal: [
  { name: 'clk',  wave: 'p......' },
  {},                                              // spacer
  ['Master',                                       // group
    { name: 'mosi', wave: '0.=.=.=', data: ['0xA5','0x33','0xFF'] },
    { name: 'cs_n', wave: '10....1' },
  ],
  ['Slave',
    { name: 'miso', wave: 'z..=.=z', data: ['0x01','0xFF'] },
  ],
]}
```

### Edge annotations

Define anchor points with `node:` on individual signals, then list edges at the top level:

```json5
{ signal: [
  { name: 'req', wave: '0.1...0', node: '..a...b' },
  { name: 'ack', wave: '0....10', node: '.....c.' },
],
  edge: ['a~>c setup', 'c~>b hold'],
}
```

Edge connector syntax: `<from><kind><to> [label]`. Kinds:
- `-` straight  `~` curved  `-~` straight-then-curve  `~-` curve-then-straight
- `->` solid arrow at target  `~>` curved arrow  `<->` arrows both ends  `-|>` orthogonal-elbow arrow
- `|` vertical drop  `|->` vertical with arrow

### head / foot

```json5
head: {
  text:  'My Diagram',
  tick:  0,        // numbers starting at N (e.g. 0, 1, 2, ...)
  tock:  0,        // numbers offset by half period
  every: 2,        // label every Nth cycle
}
```

### Common patterns

**Clock with enable:**
```json5
{ signal: [
  { name: 'clk', wave: 'p.......' },
  { name: 'en',  wave: '0.1...0.' },
  { name: 'q',   wave: 'x.==.x..', data: ['D0','D1'] },
]}
```

**SPI write (Mode 0):**
```json5
{ signal: [
  { name: 'sclk', wave: '0.p....0' },
  { name: 'cs_n', wave: '10.....1' },
  { name: 'mosi', wave: 'x=======x', data: ['b7','b6','b5','b4','b3','b2','b1','b0'] },
  { name: 'miso', wave: 'z.......z' },
]}
```

**Request / acknowledge handshake:**
```json5
{ signal: [
  { name: 'req',  wave: '0.1..0..', node: '..a..b..' },
  { name: 'ack',  wave: '0..1.0..', node: '...c.d..' },
  { name: 'data', wave: 'x.=..x..', data: ['payload'] },
],
  edge: ['a~>c req→ack', 'b~>d clear'],
}
```

## Variant 2: reg (bitfield / register layout)

The top-level **is** the array — no wrapping object, no `signal` key.

### Field object

```json5
{
  name:   'FIELD',  // optional — omit for reserved/unused gaps
  bits:   4,        // required — width in bits
  attr:   'RW',     // optional — access type or arbitrary label; can be array for multiple rows
  type:   2,        // optional — color (0=white, 2=orange, 3=yellow, 4=red, 5=green, 6=cyan, 7=blue)
  rotate: 0,        // optional — label rotation: -90, 0, 90
}
```

### Example: 32-bit control register

```json5
[
  { name: 'IPO',      bits: 8, attr: 'RO' },
  {                   bits: 7 },                       // reserved
  { name: 'BRK',      bits: 5, attr: 'RW', type: 4 },
  { name: 'CPK',      bits: 1 },
  { name: 'Clear',    bits: 3 },
  {                   bits: 8 },                       // reserved high bits
]
```

Top-level options can be added by wrapping the array:

```json5
{
  reg: [ /* fields */ ],
  config: { lanes: 2, hspace: 888 },   // lanes: rows of fields; hspace: width in px
}
```

## Variant 3: assign (logic schematic)

`assign` holds an array of circuits. Each circuit is `[outputName, tree]`, where the tree is `[operator, ...operands]`. Operands are either signal names or nested trees.

```json5
{ assign: [
  ['out',
    ['XNOR',
      ['NAND',
        ['INV', 'a'],
        ['NOR', 'b', ['BUF', 'c']],
      ],
      ['AND',
        ['XOR', 'd', 'e', ['OR', 'f', 'g']],
        'h',
      ],
    ],
  ],
]}
```

**Operators:** `AND`, `OR`, `XOR`, `NAND`, `NOR`, `XNOR`, `INV`, `BUF`. Symbolic equivalents: `&`, `|`, `^`, `~&`, `~|`, `~^`, `~`, `=`.

## File naming

- Descriptive filename based on diagram content (`spi-write`, `axi-handshake`, `control-register`).
- Lowercase with hyphens for multi-word names.
- Use the `.json5` extension for source files (JSON5 is supported natively by `wavedrom-cli`).
- For exports, use double extensions: `name.json5.svg`, `name.json5.png`, `name.json5.pdf` — signals that the source was WaveJSON.
- After a successful export, keep the `.json5` source (unlike drawio, WaveDrom exports do not embed the source — the `.json5` file is the only editable form).

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `wavedrom-cli: command not found` | Not installed or not on PATH | `npm i -g wavedrom-cli`; or paste WaveJSON into https://wavedrom.com/editor.html |
| Wave length mismatch across signals | Different number of characters in `wave:` | All `wave:` strings in one diagram should have the same length (after accounting for `period`) |
| Data labels appear on the wrong cells | `data:` array consumed out of order | Labels in `data:` are consumed left-to-right by `=` and `2-9` cells only; `.` and `x` do not consume |
| Output SVG renders blank | Invalid JSON5 (trailing operator, unquoted reserved word) | Validate by running `wavedrom-cli -i file.json5 -s /tmp/test.svg` and reading stderr |
| Bitfield total ≠ register width | Sum of `bits:` does not match expected width | The diagram renders whatever total you provide; add a reserved `{ bits: N }` gap to pad |
| Edge label arrow not appearing | Anchor character not in `node:` string | `node:` must have the same length as `wave:`; anchor chars are letters at the right column |

## References

- WaveDrom homepage and live editor: https://wavedrom.com/ — https://wavedrom.com/editor.html
- Signal tutorial: https://wavedrom.com/tutorial.html
- Logic-schematic tutorial: https://wavedrom.com/tutorial2.html
- WaveJSON schema: https://github.com/wavedrom/schema
- Bitfield package (reg variant): https://github.com/wavedrom/bitfield
- CLI: https://github.com/wavedrom/wavedrom-cli

## CRITICAL: JSON5 well-formedness

- Output must parse as JSON5. Unquoted keys and single-quoted strings are fine; trailing commas in arrays/objects are fine; comments (`// ...`, `/* ... */`) are fine.
- Never emit `undefined` or JavaScript expressions — only JSON5-valid literals.
- `wave:`, `data:`, `node:`, and `attr:` strings/arrays inside one signal entry should be length-coherent (one position in `wave:` is one period; `node:` mirrors that grid; `data:` consumes one entry per `=`/`2-9`).
