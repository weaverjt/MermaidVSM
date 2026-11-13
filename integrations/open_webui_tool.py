"""
title: Mermaid Studio VSM Viewer
author: ILCJT
description: Renders a .vsm.json project (Mermaid + VSM metrics) in an embedded Mermaid Studio iframe.
requirements:
version: 1.2.1
"""

import base64
import html
import json
from typing import Any, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# allow-same-origin together with allow-scripts is only safe because Mermaid Studio is
# served from a DIFFERENT origin than Open WebUI. Never point `studio_url` at the
# Open WebUI origin itself with these flags, or the frame can escape its sandbox.
SANDBOX = "allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
ICON_KEYS = {
    "process_dedicated", "process_shared", "workcell", "supermarket", "safety_stock",
    "fifo", "data_box", "inspection", "supplier", "customer", "milk_run", "actor",
    "kaizen", "scissors", "cloud", "truck", "plane", "document", "clock", "box",
    "push", "pull",
}
NODE_CATEGORIES = {"process", "inventory", "information", "transport", "people", "event", "external", "flow"}
FLOW_TYPES = {"material-push", "material-pull", "information-manual", "information-electronic", "callout"}
EDGE_ARROWS = {"directed", "bidirectional", "circle", "double_circle", "cross", "double_cross", "open", "none"}


def validate_project_state(state: Any) -> None:
    """Validate metadata consumed by Studio without modifying the project payload."""
    if not isinstance(state, dict) or not isinstance(state.get("mermaid"), str) or not state["mermaid"].strip():
        raise ValueError('JSON must contain a non-empty "mermaid" field.')
    version = state.get("schemaVersion")
    if version is not None and (type(version) is not int or version != 1):
        raise ValueError('"schemaVersion" must be 1 when provided.')
    for section in ("metrics", "nodes", "styles", "edges", "notes"):
        value = state.get(section)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f'"{section}" must be an object.')
    for section in ("metrics", "nodes", "styles", "edges", "notes"):
        entries = state.get(section, {})
        for key, entry in entries.items():
            if not isinstance(key, str) or not isinstance(entry, dict):
                raise ValueError(f'Each "{section}" entry must be an object keyed by a string.')
    for node_id, metadata in (state.get("nodes") or {}).items():
        if metadata.get("icon") is not None and metadata["icon"] not in ICON_KEYS:
            raise ValueError(f'Unsupported icon for node "{node_id}".')
        if metadata.get("category") is not None and metadata["category"] not in NODE_CATEGORIES:
            raise ValueError(f'Unsupported category for node "{node_id}".')
    for node_id, metrics in (state.get("metrics") or {}).items():
        if metrics.get("icon") is not None and metrics["icon"] not in ICON_KEYS:
            raise ValueError(f'Unsupported legacy metric icon for node "{node_id}".')
    for edge_id, edge in (state.get("edges") or {}).items():
        if edge.get("flowType") is not None and edge["flowType"] not in FLOW_TYPES:
            raise ValueError(f'Unsupported flowType for edge "{edge_id}".')
        if edge.get("arrow") is not None and edge["arrow"] not in EDGE_ARROWS:
            raise ValueError(f'Unsupported arrow for edge "{edge_id}".')
        for endpoint in ("source", "target"):
            if edge.get(endpoint) is not None and (not isinstance(edge[endpoint], str) or not edge[endpoint]):
                raise ValueError(f'Edge "{edge_id}" has an invalid {endpoint}.')
        if edge.get("index") is not None and (type(edge["index"]) is not int or edge["index"] < 0):
            raise ValueError(f'Edge "{edge_id}" index must be a non-negative integer.')
    for note_id, note in (state.get("notes") or {}).items():
        if not isinstance(note.get("targetId"), str) or not note["targetId"]:
            raise ValueError(f'Note "{note_id}" must have a non-empty targetId.')


def encode_state(state: Union[dict, str]) -> str:
    """Encode a project as UTF-8 JSON and unpadded base64url."""
    if isinstance(state, str):
        state = json.loads(state)
    raw = json.dumps(state, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def studio_address(url: str, encoded: str) -> tuple[str, str]:
    """Return the base URL and state URL for the configured studio."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Studio URL must be an HTTP(S) URL without credentials.")
    _ = parts.port
    if parts.fragment:
        raise ValueError("Studio URL must not contain a fragment.")
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "state"]
    base = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    return base, f"{base}#state={encoded}"


def script_json(value: Any) -> str:
    """Encode JSON safely inside an HTML script element."""
    return (json.dumps(value, ensure_ascii=True)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


class Tools:
    class Valves(BaseModel):
        studio_url: str = Field(
            default="https://weaverjt.github.io/MermaidVSM/src/mermaid_studio.html",
            description="Where Mermaid Studio is hosted (use the bundled build for internal hosting).",
        )
        iframe_height: int = Field(default=640, description="Iframe height in pixels.")
        max_url_chars: int = Field(
            default=7000,
            description="Above this URL length the state is delivered via postMessage instead of a hash.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def render_vsm(self, mermaid_code: str, title: str = "Value Stream Map") -> HTMLResponse:
        """
        Open one interactive MermaidVSM canvas for Mermaid flowchart code.
        Each call creates a separate embedded canvas. Call once per requested map,
        not repeatedly to test or revise it.
        :param mermaid_code: Mermaid diagram source, without Markdown code fences.
        :param title: Title for the new canvas.
        """
        if not isinstance(mermaid_code, str) or not mermaid_code.strip():
            return self._error("Mermaid code must be a non-empty string.")
        if not isinstance(title, str):
            return self._error("Title must be a string.")
        return self._render({"title": title.strip() or "Value Stream Map", "mermaid": mermaid_code})

    def open_vsm_studio(self, project_json: str) -> HTMLResponse:
        """
        Open one Value Stream Map / process flow in Mermaid Studio.
        Each call creates a separate embedded canvas. Use this OR render_vsm once
        per requested map, not both or repeated calls to test or revise it.
        :param project_json: A .vsm.json document as JSON, optionally including schemaVersion, nodes, edges, and notes metadata.
        """
        try:
            state: Any = json.loads(project_json)
            validate_project_state(state)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            return self._error(f"Invalid VSM JSON: {exc}")
        return self._render(state)

    def _error(self, message: str) -> HTMLResponse:
        return HTMLResponse(
            content=f"<p>{html.escape(message)}</p>",
            headers={"Content-Disposition": "inline"},
        )

    def _render(self, state: dict) -> HTMLResponse:
        try:
            base, url = studio_address(self.valves.studio_url, encode_state(state))
        except ValueError as exc:
            return self._error(f"Invalid Studio URL: {exc}")
        use_post_message = len(url) > self.valves.max_url_chars
        script = ""
        if use_post_message:
            # Register before navigating so a fast iframe cannot send vsm:ready first.
            script = (
                "<script>(function(){var f=document.getElementById('vsm');"
                f"var s={script_json(state)},url={script_json(base)},origin=new URL(url).origin;"
                "var status=document.getElementById('vsm-error');"
                "var timer=setTimeout(function(){status.textContent='Studio did not confirm the project load. Check embedding permissions or open a project file directly.';},15000);"
                "window.addEventListener('message',function(e){"
                "if(e.source!==f.contentWindow||(e.origin!==origin&&e.origin!=='null')||!e.data)return;"
                "if(e.data.type==='vsm:ready')"
                "f.contentWindow.postMessage({type:'vsm:load',state:s},e.origin==='null'?'*':origin);"
                "if(e.data.type==='vsm:loaded'){clearTimeout(timer);status.textContent='';}"
                "if(e.data.type==='vsm:error'){clearTimeout(timer);"
                "status.textContent='Studio could not load the project: '+e.data.message;}"
                "});f.src=url;})();</script>"
            )

        body = (
            '<iframe id="vsm" title="Mermaid Studio" '
            + ("" if use_post_message else f'src="{html.escape(url, quote=True)}" ')
            + f'sandbox="{SANDBOX}" allow="fullscreen" allowfullscreen '
            f'style="width:100%;height:{int(self.valves.iframe_height)}px;border:0;background:#020617"></iframe>'
            + ('<p id="vsm-error" role="alert">Loading project; JavaScript and iframe embedding must be enabled.</p>' if use_post_message else "")
            + script
            + "<script>(function(){function reportHeight(){parent.postMessage({type:'iframe:height',height:document.documentElement.scrollHeight},'*');}"
              "window.addEventListener('load',reportHeight);new ResizeObserver(reportHeight).observe(document.body);})();</script>"
        )
        return HTMLResponse(content=body, headers={"Content-Disposition": "inline"})
