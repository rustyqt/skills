# Technical block / architecture diagrams (ports, straight arrows, custom shapes)

For precise hardware/software block diagrams (entity ports, sub-blocks, signal arrows) the default
flowchart workflow (ELK auto-layout, no `exitX/entryX`) produces bendy, diagonal, or overlapping
arrows. Generate these from a **parametric script** with computed coordinates and explicit, aligned
connection points instead. The open-logic scrubber RAM wrapper diagrams were built this way.

## When to use this (instead of the default flowchart workflow)

- The user wants straight, boundary-to-boundary arrows, no overlaps, equidistant/centered ports.
- Block shapes are non-rectangular (a "U-shape" wrapper, an L, a notched block, ...).
- The artifact is an *editable PNG* (`*.drawio.png`) that must be updated in place.

## Editing an existing diagram in place (do NOT create a parallel source file)

open-logic (and many repos) store diagrams as **editable PNGs**: `name.drawio.png` is a PNG with the
diagram XML embedded as a zlib-compressed `mxGraphModel` in a `zTXt` chunk — there is no separate
`.drawio`. When asked to update such a diagram:

1. Update IN PLACE: re-export over the SAME `name.drawio.png` with `--embed-diagram`. Do NOT create a
   new `name.drawio` beside it (that leaves two sources and breaks the repo convention).
2. To recover the current source from an editable PNG (tweak instead of redraw):

   ```python
   import struct, zlib, urllib.parse
   d = open(f, 'rb').read(); i = 8; val = None
   while i < len(d) - 8:
       ln = struct.unpack('>I', d[i:i+4])[0]; t = d[i+4:i+8]
       if t == b'zTXt':
           kw, rest = d[i+8:i+8+ln].split(b'\x00', 1)   # rest[0] = compression-method byte
           val = zlib.decompress(rest[1:]).decode('utf-8', 'replace')
       i += 12 + ln
       if t == b'IEND': break
   xml = urllib.parse.unquote(val)   # the <mxfile>...</mxfile>
   ```

3. After export, re-read the `zTXt` to confirm the embedded XML is the NEW diagram (still editable),
   and `Read` the PNG to eyeball it.

## Custom (non-rectangular) shapes via inline stencils

drawio has no built-in U/L/notched block. Define a **stencil** (0..100 w x h path) and inline-encode
it into the cell style. A U (two arms 14% wide, bottom bar 22% tall, open top-middle):

```text
<shape h="100" w="100" aspect="variable" strokewidth="inherit"><connections/><foreground>
<path><move x="0" y="0"/><line x="14" y="0"/><line x="14" y="78"/><line x="86" y="78"/>
<line x="86" y="0"/><line x="100" y="0"/><line x="100" y="100"/><line x="0" y="100"/><close/></path>
<fillstroke/></foreground></shape>
```

Encode it exactly as drawio's `Graph.compress` does — `base64(deflateRaw(encodeURIComponent(xml)))` —
and use it as `shape=stencil(<that>)`:

```python
import zlib, base64, urllib.parse
def enc_stencil(xml):
    e = urllib.parse.quote(xml, safe="!~*'()-_.")     # encodeURIComponent
    co = zlib.compressobj(9, zlib.DEFLATED, -15)       # raw deflate (no zlib header/trailer)
    return base64.b64encode(co.compress(e.encode()) + co.flush()).decode()
style = f"shape=stencil({enc_stencil(U_XML)});whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
```

Verify the stencil renders with a 1-shape throwaway diagram BEFORE building the full figure.

### Connection-point caveat (the cause of diagonal arrows)

For a stencil, drawio only honours fixed `exitX/entryX` cleanly on the **bounding-box perimeter**
(left x=0, right x=1, top y=0, bottom y=1). Points on an INNER edge (a U arm's inner wall at
x=0.14/0.86) get snapped, so arrows to/from them come out diagonal. For straight arrows to/from inner
walls, anchor that end with a **fixed absolute point** (`sourcePoint`/`targetPoint`), not a fraction:

```text
<mxCell ... edge="1" target="ram"><mxGeometry relative="1" as="geometry">
  <mxPoint x="353" y="220" as="sourcePoint"/></mxGeometry></mxCell>
```

Perimeter connections (inputs on the left edge, outputs on the right edge, ErrInj on the top) work
fine with `exitX/entryX` fractions.

## Straight, boundary-to-boundary arrows

- A straight edge needs source and target connection points at the **same Y** (horizontal) or same
  **X** (vertical). Compute both ends to align, and use a plain edge (no `edgeStyle=orthogonal...`,
  no ELK auto-route) so it draws as one direct line.
- Drive every coordinate from a small Python generator: place the blocks, then for each signal
  compute the exit/entry fraction from the chosen absolute Y. This makes "all arrows straight",
  "equidistant ports", "centered output" trivial, and turns later tweaks (move a group, shorten the
  arrows, reorder ports) into one-line edits + re-export.

## Quality checklist (apply to the FIRST version, not after review)

- [ ] Every arrow is pure horizontal or vertical (no diagonals, no orthogonal step-bends).
- [ ] Every arrow starts and ends on a module boundary (block edge or port label) — never mid-air,
      never mid-block, and never passing THROUGH a block (route the signal into the block it enters).
- [ ] No overlaps: distinct Y per arrow; each label fits inside its gap; labels never sit on blocks.
- [ ] Arrows are a readable length (~50-60px), not stubs — widen the label-to-block margin if needed.
- [ ] Port/signal order matches the entity's declared port order; show signals individually unless
      the user asks to bundle.
- [ ] Block labels centered where intended (e.g. in a U's bottom bar via `verticalAlign=bottom` +
      `spacingBottom`).

## CLI gotcha: multi-page export

`-p/--page-index` is unreliable for multi-page files (it often exports page 0 regardless). Export
each page reliably by extracting the wanted `<diagram>` into its own single-page temp `.drawio`
first, then exporting that. (Or keep one editable PNG per diagram, the open-logic convention.)
