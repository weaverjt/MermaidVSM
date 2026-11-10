# Mermaid Studio (MermaidVSM)

## Overview

Mermaid Studio is an interactive, single-file HTML / ES6 / Tailwind CSS workspace for Value Stream Mapping and process diagrams. It renders Mermaid.js diagrams on a full-screen canvas with floating HUD panels for editing, inspecting and measuring a process. Everything runs in the browser, with no build step, no login and no backend. Process data never leaves your machine.

**Live URL:** <https://ilcjt.github.io/MermaidVSM/src/mermaid_studio.html>

## Features

- **Dynamic SVG drag-and-drop:** drag flowchart and state-diagram nodes on the canvas. Works with mouse, pen and touch (Pointer Events, >4px movement starts a drag, a tap selects). Offsets are saved per node in `projectState.positions[id]` and re-applied after every render.
- **Gooey Bezier line routing:** connected edges are redrawn as cubic Bezier curves while you drag, and `#gooey-anchor` SVG-filtered anchor sockets appear on the dragged node.
- **Node / Edge inspector:** a floating drawer for node title (including bold), fill/border colors, shape, icon, owner, C/T, C/O, WIP and friction, and for connector label, line style and arrowhead. Edits write back into the Mermaid code live.
- **Inspector selection:** select a node, connector, note or subgraph on the canvas to open its inspector. Other inspector tabs are disabled until an item of that type is selected.
- **Subgraph inspector:** activate the Cluster Wand to select a flowchart container and edit its title, fill, opacity and border, or make its background transparent. Drag the container to move its nested nodes, subgraphs and attached notes together; connected lines update as it moves. Turn the wand off or close the inspector to return to pointer mode. Ungroup preserves its contents; deleting the container and contents requires confirmation. Styles are stored in Mermaid code and project files; container positions are stored in project files.
- **Standalone Lean shapes:** VSM symbols, including safety stock, FIFO lane, data box, dedicated/shared process, workcell, supplier, customer, milk run, supermarket and inspection, appear as resizable standalone vectors with titles underneath.
- **Basic shapes:** The Object Library and Node Shape inspector include rectangles, circles, diamonds, cylinders and parallelograms.
- **Multiple selection and grouping:** Shift-click flowchart nodes, or drag an empty canvas area with Shift held. The Select Area button also enables area selection without a keyboard; Escape clears the selection. Select at least two nodes and choose **Group into Subgraph** to create a top-level subgraph, including nodes from different parents. Nodes retain their positions, notes and connections; the new container automatically fits its contents. Original empty parent wrappers remain in the code, although Mermaid may not display them. Mermaid code that cannot be safely regrouped is left unchanged.
- **VSM connectors:** the Edge Inspector offers zigzag electronic information flow, striped push flow, and double circle/cross arrowheads. The custom visual styles persist in project files and `?state=` links; Mermaid text exports retain their standard dotted or thick connectors rather than the custom appearance.
- **Bottom metric sub-pills:** Owner 👤, Cycle Time ⏱️, Changeover 🔄 and WIP 📦 render under the node title.
- **VSM summary ladder:** VA time, lead time, total WIP, friction points and efficiency update live.
- **Object Library:** add shapes and VSM symbols without automatically opening the inspector (`projectState.settings.autoOpenInspector` defaults to `false`). Connect Wand chains nodes; Disconnect Wand removes a clicked connection or the connection between two selected nodes without moving the nodes. When multiple connections exist between two nodes, click the specific line. Either wand stays active until a background click or Escape. Select a node or edge to delete it from the inspector; use Node Shape to switch between containers and standalone symbols.
- **Canvas tabs and templates:** Each Blank Canvas or template starts a separate tab without replacing existing work. Tabs are automatically restored in the same browser; closing a tab with work requires confirmation. Browser storage can be cleared or unavailable, and autosave pauses if another browser tab changes the workspace.
- **Included templates:** Value Stream Map, Standard Process Flow, RMA Departmental Swimlanes (CS/TS/WH/TI/AP lanes, with metrics, icons and a CS-to-TS handoff note), RMA Sequence Handoff (`graph LR` with a $750 decision gate), State Machine and Root Cause Tree.
- **Base64 URL parameter state hydration:** open a project from a link with `?state=<base64 of a .vsm.json>` (see below).
- **Process Notes:** select a node and click **📝 Add Note** in the inspector to attach a draggable yellow note card with a dashed connector. Notes are saved in `.vsm.json` and included in PNG/SVG exports.
- **Import / export:** **Open Project** or drag a file anywhere onto the app to add its canvases without replacing existing tabs. **Save / Export** can save the current canvas or all tabs as a versioned `.vsm` project, including canvas data and the active tab; existing `.vsm.json` files remain supported. PNG, SVG, Mermaid text and legacy single-canvas JSON export remain available. Native file pickers are used where supported; otherwise the browser file input and download are used.

### Project files and double-click

Use **Save / Export → Save All Tabs** for a portable workspace backup, or **Save Current Canvas** for one canvas. Opening a workspace adds its tabs to the existing session and selects its saved active tab. `.vsm` files are JSON and can be reopened through the app; merely changing the extension does **not** make the operating system launch it on double-click.

If the native save dialog is unavailable (for example, in some embedded or automated browsers), use **Download All Tabs** or **Download Current Canvas** instead. The browser chooses the download location; check its downloads to confirm the file was actually saved. Cancelling a native picker does not automatically download a file.

Desktop double-click integration is future work: it requires an installed, HTTPS-hosted PWA with a manifest `file_handlers` declaration and a `launchQueue` consumer, plus browser and OS permission/default-app selection. Support is limited to compatible desktop Chromium-based browsers; the standalone `file:` bundle does not register file associations. See [MDN's file handling guide](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Associate_files_with_your_PWA).

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

Below 768px the Object Library, Node/Edge Inspector and Code editor become full-width bottom sheets above the summary bar, each with a grab handle (swipe down to close or minimize, swipe up to expand, tap to toggle). Only one sheet is open at a time; opening the inspector hides the library and editor. Open Project, Save / Export, Add and Code move to a floating bottom navigation bar. Buttons, menu items and library/inspector controls are at least 44px; standalone symbols and edge connectors have zoom-independent 44px touch targets. The canvas uses `touch-action: none` with `user-select: none` (no pull-to-refresh or text selection); one finger drags nodes or pans, two fingers pinch-zoom. While a wand is active, canvas panning is disabled; tap the background to exit the wand and restore panning. Panels respect `env(safe-area-inset-bottom)`. Reload after resizing across the breakpoint to reset the editor state.

The `.desktop-only` utility hides future desktop-only controls at widths of 640px and below; collaboration and GitHub commit controls are not yet implemented.

## Documentation

See [`docs/`](docs): project charter, architecture spec, decision log, current state and the `.vsm.json` builder skill.
