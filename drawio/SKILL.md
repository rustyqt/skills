---
name: drawio
description: Always use when user asks to create, generate, draw, or design a diagram, flowchart, architecture diagram, ER diagram, sequence diagram, class diagram, network diagram, mockup, wireframe, or UI sketch, or mentions draw.io, drawio, drawoi, .drawio files, or diagram export to PNG/SVG/PDF.
---

# Draw.io Diagram Skill

Generate draw.io diagrams as native `.drawio` files. Optionally export to PNG, SVG, or PDF with the diagram XML embedded (so the exported file remains editable in draw.io).

## How to create a diagram

1. **Generate draw.io XML** in mxGraphModel format for the requested diagram
2. **Write the XML** to a `.drawio` file in the current working directory using the Write tool
3. **If the user requested an export format** (png, svg, pdf), locate the draw.io CLI (see below), export with `--embed-diagram`, then delete the source `.drawio` file. If the CLI is not found, keep the `.drawio` file and tell the user they can install the draw.io desktop app to enable export, or open the `.drawio` file directly
4. **Render-and-verify (MANDATORY when exporting to PNG/SVG/JPG).** After exporting an image, immediately use the Read tool on the exported file to visually inspect what was rendered. Check for: (a) every arrow ends on a block boundary (no floating arrows), (b) no overlapping text/labels, (c) labels sit on the intended edges (not on adjacent blocks), (d) parallel/sibling edges aren't bundled into a single line, (e) every cell is inside the page bounds. If any issue is found, fix the XML and re-export — do not present a broken diagram to the user. PDFs and pure-text exports are exempt; everything image-based needs the visual pass.
5. **Open the result** — the exported file if exported, or the `.drawio` file otherwise. If the open command fails, print the file path so the user can open it manually

## Choosing the output format

Check the user's request for a format preference. Examples:

- `/drawio create a flowchart` → `flowchart.drawio`
- `/drawio png flowchart for login` → `login-flow.drawio.png`
- `/drawio svg: ER diagram` → `er-diagram.drawio.svg`
- `/drawio pdf architecture overview` → `architecture-overview.drawio.pdf`

If no format is mentioned, just write the `.drawio` file and open it in draw.io. The user can always ask to export later.

### Supported export formats

| Format | Embed XML | Notes |
|--------|-----------|-------|
| `png` | Yes (`-e`) | Viewable everywhere, editable in draw.io |
| `svg` | Yes (`-e`) | Scalable, editable in draw.io |
| `pdf` | Yes (`-e`) | Printable, editable in draw.io |
| `jpg` | No | Lossy, no embedded XML support |

PNG, SVG, and PDF all support `--embed-diagram` — the exported file contains the full diagram XML, so opening it in draw.io recovers the editable diagram.

## draw.io CLI

The draw.io desktop app includes a command-line interface for exporting.

### Locating the CLI

First, detect the environment, then locate the CLI accordingly:

#### WSL2 (Windows Subsystem for Linux)

WSL2 is detected when `/proc/version` contains `microsoft` or `WSL`:

```bash
grep -qi microsoft /proc/version 2>/dev/null && echo "WSL2"
```

On WSL2, use the Windows draw.io Desktop executable via `/mnt/c/...`:

```bash
DRAWIO_CMD=`/mnt/c/Program Files/draw.io/draw.io.exe`
```

The backtick quoting is required to handle the space in `Program Files` in bash.

If draw.io is installed in a non-default location, check common alternatives:

```bash
# Default install path
`/mnt/c/Program Files/draw.io/draw.io.exe`

# Per-user install (if the above does not exist)
`/mnt/c/Users/$WIN_USER/AppData/Local/Programs/draw.io/draw.io.exe`
```

#### macOS

```bash
/Applications/draw.io.app/Contents/MacOS/draw.io
```

#### Linux (native)

```bash
drawio   # typically on PATH via snap/apt/flatpak
```

#### Windows (native, non-WSL2)

```
"C:\Program Files\draw.io\draw.io.exe"
```

Use `which drawio` (or `where drawio` on Windows) to check if it's on PATH before falling back to the platform-specific path.

### Export command

```bash
drawio -x -f <format> -e -b 10 -o <output> <input.drawio>
```

**WSL2 example:**

```bash
`/mnt/c/Program Files/draw.io/draw.io.exe` -x -f png -e -b 10 -o diagram.drawio.png diagram.drawio
```

Key flags:
- `-x` / `--export`: export mode
- `-f` / `--format`: output format (png, svg, pdf, jpg)
- `-e` / `--embed-diagram`: embed diagram XML in the output (PNG, SVG, PDF only)
- `-o` / `--output`: output file path
- `-b` / `--border`: border width around diagram (default: 0)
- `-t` / `--transparent`: transparent background (PNG only)
- `-s` / `--scale`: scale the diagram size
- `--width` / `--height`: fit into specified dimensions (preserves aspect ratio)
- `-a` / `--all-pages`: export all pages (PDF only)
- `-p` / `--page-index`: select a specific page (1-based)

### Opening the result

| Environment | Command |
|-------------|---------|
| macOS | `open <file>` |
| Linux (native) | `xdg-open <file>` |
| WSL2 | `cmd.exe /c start "" "$(wslpath -w <file>)"` |
| Windows | `start <file>` |

**WSL2 notes:**
- `wslpath -w <file>` converts a WSL2 path (e.g. `/home/user/diagram.drawio`) to a Windows path (e.g. `C:\Users\...`). This is required because `cmd.exe` cannot resolve `/mnt/c/...` style paths.
- The empty string `""` after `start` is required to prevent `start` from interpreting the filename as a window title.

**WSL2 example:**

```bash
cmd.exe /c start "" "$(wslpath -w diagram.drawio)"
```

## File naming

- Use a descriptive filename based on the diagram content (e.g., `login-flow`, `database-schema`)
- Use lowercase with hyphens for multi-word names
- For export, use double extensions: `name.drawio.png`, `name.drawio.svg`, `name.drawio.pdf` — this signals the file contains embedded diagram XML
- After a successful export, delete the intermediate `.drawio` file — the exported file contains the full diagram

## XML format

A `.drawio` file is native mxGraphModel XML. Always generate XML directly — Mermaid and CSV formats require server-side conversion and cannot be saved as native files.

### Basic structure

Every diagram must have this structure:

```xml
<mxGraphModel adaptiveColors="auto">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Diagram cells go here with parent="1" -->
  </root>
</mxGraphModel>
```

- Cell `id="0"` is the root layer
- Cell `id="1"` is the default parent layer
- All diagram elements use `parent="1"` unless using multiple layers

## References

Three companion files ship with this skill. Read them when the section below says to — the SKILL.md is intentionally short and offloads the deep reference material.

- [`xml-reference.md`](./xml-reference.md) — **Read first for every XML diagram.** Reasoning-budget guidance (don't compute coordinates, don't debate layout, use the rigid 180×120 grid), common styles for rectangles / diamonds / edges, edge-routing rules (every edge needs `<mxGeometry relative="1" as="geometry" />`; ELK auto-routes — no waypoints / `exitX` / `entryX`), containers and swimlanes (flat lanes for BPMN, nested swimlanes for cloud/infra, table layout for cross-functional grids), layers, tags, metadata + `%placeholder%` substitution, dark-mode color handling, and the `postLayout` algorithms (`verticalFlow`, `horizontalFlow`, `tree`, `force`, `stress`, `radial`).
- [`style-reference.md`](./style-reference.md) — **Look up when picking a shape or style property.** Companion to `mxfile.xsd`. Full file-structure rules (the mandatory `id="0"` root and `id="1"` default layer, vertex/edge mutual exclusivity, coordinate origin), the complete shape catalog (core mxGraph + extended drawio shapes like `cylinder3` / `card` / `callout` + UML shapes + stencil libraries: `mxgraph.flowchart.*`, `mxgraph.aws4.*`, `mxgraph.cisco.*`, `mxgraph.kubernetes.*`, etc.), every style property table (fill/stroke, geometry, text, edges, arrow markers, connection points, swimlanes, images, sketch mode, behavior flags), edge routing algorithms, perimeter types, predefined style classes (`text`, `edgeLabel`, color themes like `blue` / `green` / `red`), HTML label patterns, layers and groups, complete worked examples (flowchart, UML class, network with groups, UserObject metadata), and a 14-point validation checklist.
- [`mermaid-reference.md`](./mermaid-reference.md) — **Consult only when the user explicitly asks for Mermaid.** Hints for the 26 Mermaid diagram types draw.io's parser supports (`flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`, `gantt`, `gitGraph`, `mindmap`, `timeline`, `quadrantChart`, `requirementDiagram`, `sankey-beta`, `xychart-beta`, `block-beta`, `c4Context`, `architecture-beta`, `radar-beta`, `packet-beta`, `venn-beta`, `treemap-beta`, `treeView-beta`, `ishikawa-beta`, `kanban`, `zenuml`, `journey`, `pie`) with syntax + styling notes for each. Mermaid cannot be saved as a native `.drawio` file, so this skill defaults to XML; this reference is only useful if the user wants Mermaid source they'll paste into draw.io's "Insert > Advanced > Mermaid" dialog.

XML schema: [`mxfile.xsd`](./mxfile.xsd) — formal schema for `.drawio` files. Consult only to resolve ambiguity about attribute names / types.

**Default workflow:** open `xml-reference.md` before generating any diagram; jump to `style-reference.md` for shape and style lookups as needed.

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| draw.io CLI not found | Desktop app not installed or not on PATH | **Offer to install it for the user with one of the one-liners below** (then re-run the export). Only fall back to "keep the `.drawio` file" if the install is refused or fails. |
| Export produces empty/corrupt file | Invalid XML (e.g. double hyphens in comments, unescaped special characters) | Validate XML well-formedness before writing; see the XML well-formedness section below |
| Diagram opens but looks blank | Missing root cells `id="0"` and `id="1"` | Ensure the basic mxGraphModel structure is complete |
| Edges not rendering | Edge mxCell is self-closing (no child mxGeometry element) | Every edge must have `<mxGeometry relative="1" as="geometry" />` as a child element |
| File won't open after export | Incorrect file path or missing file association | Print the absolute file path so the user can open it manually |

### Installing draw.io desktop

When the CLI isn't found, the desktop app can be installed with a single command (no reboot needed). Pick the matching platform and offer to run it for the user:

| Platform | Install command | Resulting CLI path |
|----------|-----------------|--------------------|
| Windows (winget) | `winget install JGraph.Draw --accept-source-agreements --accept-package-agreements --silent` | `C:\Program Files\draw.io\draw.io.exe` |
| Windows (Chocolatey) | `choco install drawio -y` | `C:\Program Files\draw.io\draw.io.exe` |
| macOS (Homebrew) | `brew install --cask drawio` | `/Applications/draw.io.app/Contents/MacOS/draw.io` |
| Linux (snap) | `sudo snap install drawio` | `drawio` on PATH |
| Linux (Flatpak) | `flatpak install -y flathub com.jgraph.drawio.desktop` | `flatpak run com.jgraph.drawio.desktop` |
| WSL2 | Install on the Windows host with winget (see first row); the WSL2 side then calls it via `/mnt/c/Program Files/draw.io/draw.io.exe` | Windows path |

After installation, verify the CLI is reachable with the platform's locator command (`where drawio.exe` / `which drawio`) before retrying the export.

## CRITICAL: XML well-formedness

- **NEVER include ANY XML comments (`<!-- -->`) in the output.** XML comments are strictly forbidden — they waste tokens, can cause parse errors, and serve no purpose in diagram XML.
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- Always use unique `id` values for each `mxCell`
