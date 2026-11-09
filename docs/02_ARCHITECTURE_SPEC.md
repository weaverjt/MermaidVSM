# 02_ARCHITECTURE_SPEC.md

## Tech Stack & Core Libraries
* **Frontend Runtime:** Vanilla HTML5 / ES6 JavaScript.
* **UI Styling:** Tailwind CSS (CDN).
* **Diagram Engine:** `mermaid.js` v10 (CDN).
* **Canvas Interactivity:** `svg-pan-zoom` v3.6 (CDN).
* **Icons:** Lucide Icons (CDN).

## Architectural Ownership Layers
- Layer A: System & File Entry (Single-file HTML DOM Shell, Drag-and-drop listener, Exporters)
- Layer B: State & AI Engine (In-Memory projectState JSON AST, Mermaid Serializer, Gemini VSM Skill Bridge)
- Layer C: UI/UX & Canvas (Canvas-First Floating HUD: full-bleed SVG canvas, floating Code Editor, Object Library and Inspector panels, Event Delegation)

## Phase 7 Architecture

### Canvas interaction
* **Layout:** `#previewPanel` fills the window. The editor (bottom-left), Object Library (top-left) and Inspector (top-right) are floating cards.
* **Node dragging:** pointer events on `#mermaidRender`. Coordinates come from the node's parent `getScreenCTM().inverse()` so dragging stays correct when panned or zoomed. A drag starts after 4px of movement; svg-pan-zoom panning is disabled during the drag. Flowchart and state nodes are draggable; sequence actors are not.
* **Position persistence:** the offset from Mermaid's layout position is stored in `projectState.positions[id] = {x, y}` and re-applied after each render. Dragging uses Pointer Events: a capture-phase `pointerdown` on `#mermaidRender`, `setPointerCapture` once movement exceeds 4px (below that it is a tap), `getScreenCTM().inverse()` for deltas, a second finger cancels the drag, and node IDs come from `cleanNodeId()` (strips Mermaid's `flowchart-`/`state-` prefix and numeric suffix).
* **Elastic routing:** `updateNodeConnections(nodeId)` redraws connected edges (and their hit-paths and labels) as cubic Beziers anchored at the facing side midpoints of the node boxes. The `#gooey-anchor` SVG filter (blur + color matrix) is applied to anchor sockets only while dragging.
* **Object Library:** groups basic shapes, inset double-line variants of those shapes, and process symbols; it also connects nodes (`toggleConnectMode`) and deletes the active node or edge (`deleteSelected`). Flowchart-only for adds and connects.
* **Shape rendering:** Mermaid remains the source of node and label definitions. Triangle metadata selects polygon geometry at render time; double-line metadata adds an inset, unfilled clone of the base geometry. Both custom shapes participate in resizing and SVG export.

### Node label markup (single source of truth is the Mermaid code)
A flowchart node is written atomically as `ID + shape open + "label" + shape close` by `syncNodeToMermaid`, using `SHAPE_MAP`. The label is:

```html
<span data-vsm-shape='triangle' data-vsm-double='true'>Title</span>
```

* **Shape metadata:** `data-vsm-shape` and `data-vsm-double` preserve the custom shape choice while parsing the Mermaid label.
* **Top-rim badge:** standard process icons remain vector badges over the top border. Their badge uses the node fill and selects a white stroke for dark fills or `#0f172a` for light fills.
* **Bottom sub-pill:** metric values, shown only for non-zero values.
* `parseNodeDefinition` / `splitIconLabel` strip both parts so `#inspectorTitle` always holds the clean title.

Actor, truck, plane, clock, box, scissors, Kaizen/sword, cloud, document, push, and pull icons are standalone primitives: their Mermaid node geometry is transparent, the 56px vector symbol is centered, and the title is laid out beneath it. Fill and border color controls are applied to the vector itself. The icon key remains in `data-icon`, and the parser reads the primitive layout so title and icon edits continue to round-trip through the inspector. Fill, border, and title/font colors are stored per node in `projectState.styles` and emitted as Mermaid style directives.

### Icon map (non-redundant VSM symbols)
Process icons deliberately avoid the metric emojis (👤 ⏱️ 🔄 📦).

| Key | Icon | Meaning |
|---|---|---|
| `process_dedicated` | Factory | Dedicated process |
| `process_shared` | Shared paths | Shared process |
| `workcell` | Workcell grid | Workcell |
| `supplier` | Factory / inbound | External supplier |
| `customer` | Person | Customer / recipient |
| `kaizen` | Burst | Kaizen burst |
| `milk_run` | Truck | Milk run / transport |
| `supermarket` | Shelves | Supermarket / storage |
| `inspection` | Magnifier / crosshair | Go-See / quality inspection |
| `actor` | Stick figure | Human operator |
| `scissors` | Scissors | Cutoff |
| `cloud` | Cloud | ERP / external system |
| `truck` / `plane` | Truck / plane | Ground / air freight |
| `document` | Document | SOP / traveler |
| `clock` | Clock | Lead-time wait |
| `box` | Package | Inventory |
| `push` / `pull` | Flow arrows | Push / pull flow |

### `data-icon` persistence
The badge span carries a `data-icon='<key>'` attribute, which `splitIconLabel` reads to preserve the icon while editing. `LEGACY_ICONS` keeps existing emoji badges readable while labels are migrated to vector markup.

### Friction highlighting
`class <id> friction;` lines (no semicolon in `stateDiagram-v2`) plus a single `classDef friction fill:#451a03,stroke:#f97316,stroke-width:2px,color:#ffedd5;`. The `classDef` is added when any node is flagged and removed when none are.

### Process Notes
`projectState.notes = { note_1: { targetId, text, offset: {x, y} } }`, where `offset` is the card's top-left relative to the target node's centre (in diagram units). `normalizeNotes()` validates entries on every load. Cards are drawn by `renderNotes()` into `<g id="notesLayer">` (a `note-links` group under a `note-cards` group), added inside the diagram root before svg-pan-zoom initialises, so notes pan, zoom and export with the diagram. Text is SVG `<text>`/`<tspan>` with canvas-measured word wrapping rather than `foreignObject`, so it rasterises reliably to PNG. The dashed yellow connector (`#eab308`, `8,6`) runs from the node's edge to the card and is recomputed by `placeNote()` when the card or its node is dragged. Cards reuse the shared `drag` pointer pipeline (`kind: 'note'`). Selecting a note opens a third inspector tab with a textarea; `activeNoteId` is separate from `activeNodeId` so Delete Selected cannot remove the node by accident. `pruneOrphanNotes()` runs after template/file/URL loads, before saving `.vsm.json`, and when a node is deleted; it is not run on ordinary typing edits. The selection outline (`.note-sel`) is stripped from exports.

### URL state loader
`loadStateFromURL()` runs at the end of `DOMContentLoaded`. It reads `?state=` (or `#state=`), decodes Base64/Base64url as UTF-8 JSON, requires a non-empty `mermaid` string, then sets `projectState`, the editor, the diagram and the VSM summary exactly as `loadFile` does. Invalid values show a status-bar error and leave the empty workspace in place.
