# Mermaid Studio (MermaidVSM)

## Overview

Mermaid Studio is an interactive, single-file HTML / ES6 / Tailwind CSS workspace for Value Stream Mapping and process diagrams. It renders Mermaid.js diagrams on a full-screen canvas with floating HUD panels for editing, inspecting and measuring a process. Everything runs in the browser, with no build step, no login and no backend. Process data never leaves your machine.

**Live URL:** <https://ilcjt.github.io/MermaidVSM/src/mermaid_studio.html>

## Features

- **Dynamic SVG drag-and-drop:** drag flowchart and state-diagram nodes on the canvas. Works with mouse, pen and touch (Pointer Events, >4px movement starts a drag, a tap selects). Offsets are saved per node in `projectState.positions[id]` and re-applied after every render.
- **Gooey Bezier line routing:** connected edges are redrawn as cubic Bezier curves while you drag, and `#gooey-anchor` SVG-filtered anchor sockets appear on the dragged node.
- **Node / Edge inspector:** a floating drawer for node title (including bold), fill/border colors, shape, icon, owner, C/T, C/O, WIP and friction, and for connector label, line style and arrowhead. Edits write back into the Mermaid code live.
- **Standalone Lean shapes:** VSM symbols, including safety stock, FIFO lane, data box, dedicated/shared process, workcell, supplier, customer, milk run, supermarket and inspection, appear as resizable standalone vectors with titles underneath.
- **VSM connectors:** the Edge Inspector offers zigzag electronic information flow, striped push flow, and double circle/cross arrowheads. The custom visual styles persist in project files and `?state=` links; Mermaid text exports retain their standard dotted or thick connectors rather than the custom appearance.
- **Bottom metric sub-pills:** Owner 👤, Cycle Time ⏱️, Changeover 🔄 and WIP 📦 render under the node title.
- **VSM summary ladder:** VA time, lead time, total WIP, friction points and efficiency update live.
- **Object Library:** add shapes and VSM symbols without automatically opening the inspector (`projectState.settings.autoOpenInspector` defaults to `false`). Connect Wand chains nodes; Disconnect Wand removes a clicked connection or the connection between two selected nodes without moving the nodes. When multiple connections exist between two nodes, click the specific line. Either wand stays active until a background click or Escape. Select a node or edge to delete it from the inspector; use Node Shape to switch between containers and standalone symbols.
- **Templates:** Value Stream Map, Standard Process Flow, RMA Departmental Swimlanes (CS/TS/WH/TI/AP lanes, with metrics, icons and a CS-to-TS handoff note), RMA Sequence Handoff (`graph LR` with a $750 decision gate), State Machine and Root Cause Tree.
- **Base64 URL parameter state hydration:** open a project from a link with `?state=<base64 of a .vsm.json>` (see below).
- **Process Notes:** select a node and click **📝 Add Note** in the inspector to attach a draggable yellow note card with a dashed connector. Notes are saved in `.vsm.json` and included in PNG/SVG exports.
- **Import / export:** drag-and-drop `.vsm.json` project files. A single **Save Image** menu exports PNG (2x), SVG or the raw Mermaid code (`.txt`) through the native "Save as" dialog (File System Access API) where supported, with a normal download as fallback. The `.vsm.json` project file is a secondary item in that menu. **Copy Code** in the editor card copies the raw Mermaid syntax.

## Setup / Local Running

No installation is needed. Open `src/mermaid_studio.html` in a browser, or serve it locally:

```powershell
python -m http.server 8080 --directory "src"
```

Then browse to <http://localhost:8080/mermaid_studio.html>. The page loads Mermaid, svg-pan-zoom, Tailwind and Lucide from CDNs, so it needs internet access.

## Opening a project from a URL

Append `?state=` followed by the Base64 (or Base64url) encoding of a UTF-8 `.vsm.json` document. A `#state=...` hash is accepted too. The JSON must contain a `mermaid` string.

```powershell
$b = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content project.vsm.json -Raw)))
"https://ilcjt.github.io/MermaidVSM/src/mermaid_studio.html?state=$b"
```

Browsers and servers limit URL length, so this suits small to medium projects. Use the Open button for large files.

## Embedding (Open WebUI / iframes)

- `?state=` is hydrated before the first render, so an embedded load renders once with no manual step. Base64 and base64url (padded or not) both work.
- A host page can push state with `iframe.contentWindow.postMessage({ type: 'vsm:load', state: <object | base64> }, '*')`. The app announces `vsm:ready`, then replies `vsm:loaded` or `vsm:error`. Only messages from the direct parent are accepted.
- A dark baseline style is inlined, and a warning banner appears if a CDN is blocked.
- [`integrations/open_webui_tool.py`](integrations/open_webui_tool.py) is an Open WebUI Tool that emits the iframe (`sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"`). It falls back to postMessage when the state is too large for a URL. Keep the app on a different origin from Open WebUI when using `allow-same-origin` with `allow-scripts`.
- **Offline / internal hosting:** `python scripts/build_bundle.py` writes `dist/mermaid_studio.bundle.html`, with Tailwind, Mermaid, svg-pan-zoom and Lucide inlined (about 4.4 MB, no network needed). The Tailwind Play script is inlined as-is; for a leaner build, precompile CSS with the Tailwind standalone CLI and replace that tag. Pin `lucide@latest` to a fixed version first for reproducible builds.

## Mobile

Below 768px the Object Library, Node/Edge Inspector and Code editor become full-width bottom sheets above the summary bar, each with a grab handle (swipe down to close or minimize, swipe up to expand, tap to toggle). Only one sheet is open at a time; opening the inspector hides the library and editor. Open, Save Image, Add and Code move to a floating bottom navigation bar. Buttons, menu items and library/inspector controls are at least 44px; standalone symbols and edge connectors have zoom-independent 44px touch targets. The canvas uses `touch-action: none` with `user-select: none` (no pull-to-refresh or text selection); one finger drags nodes or pans, two fingers pinch-zoom. While a wand is active, canvas panning is disabled; tap the background to exit the wand and restore panning. Panels respect `env(safe-area-inset-bottom)`. Reload after resizing across the breakpoint to reset the editor state.

The `.desktop-only` utility hides future desktop-only controls at widths of 640px and below; collaboration and GitHub commit controls are not yet implemented.

## Documentation

See [`docs/`](docs): project charter, architecture spec, decision log, current state and the `.vsm.json` builder skill.
