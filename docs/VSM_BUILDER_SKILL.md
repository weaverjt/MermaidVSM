---
name: vsm-builder
description: Generates structured .vsm.json project state files for Mermaid Studio containing Mermaid syntax and VSM process metrics (Cycle Time, Changeover, WIP, Friction Points).
---

# VSM Builder Skill

For the full Open WebUI system prompt, syntax crosswalk, and metric limitations,
see [OPEN_WEBUI_SYSTEM_PROMPT.md](OPEN_WEBUI_SYSTEM_PROMPT.md). Missing
measurements should remain unknown, not be invented or treated as measured zero.

When asked to draft or map a Value Stream Map, process flow, or RMA disposition sequence, generate a JSON object wrapped in a .vsm.json file block.

## Required JSON Schema
{
  "project": {
    "title": "<Process Title>",
    "version": "1.0",
    "updated": "2026-11-03",
    "author": "Gemini VSM Builder"
  },
  "mermaid": "<Valid Mermaid.js graph TD or LR code>",
  "metrics": {
    "<Node_ID>": {
      "title": "<Step Name>",
      "owner": "<Department Name>",
      "ct": <Cycle Time in minutes (number)>,
      "co": <Changeover Time in minutes (number)>,
      "wip": <WIP quantity in pieces (number)>,
      "friction": <true|false>
    }
  }
}
