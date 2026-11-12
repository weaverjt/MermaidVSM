"""
title: Mermaid Studio VSM Viewer
author: ILCJT
description: Renders a .vsm.json project (Mermaid + VSM metrics) in an embedded Mermaid Studio iframe.
requirements:
version: 1.2.0
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
        Render Mermaid flowchart code in the interactive MermaidVSM studio.
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
        Open a Value Stream Map / process flow in Mermaid Studio.
        :param project_json: A .vsm.json document as a JSON string ({"project":{...},"mermaid":"...","metrics":{...}}).
        """
        try:
            state: Any = json.loads(project_json)
            if not isinstance(state, dict) or not isinstance(state.get("mermaid"), str) or not state["mermaid"].strip():
                raise ValueError('JSON must contain a non-empty "mermaid" field.')
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
            + f'sandbox="{SANDBOX}" '
            f'style="width:100%;height:{int(self.valves.iframe_height)}px;border:0;background:#020617"></iframe>'
            + ('<p id="vsm-error" role="alert">Loading project; JavaScript and iframe embedding must be enabled.</p>' if use_post_message else "")
            + script
            + "<script>(function(){function reportHeight(){parent.postMessage({type:'iframe:height',height:document.documentElement.scrollHeight},'*');}"
              "window.addEventListener('load',reportHeight);new ResizeObserver(reportHeight).observe(document.body);})();</script>"
        )
        return HTMLResponse(content=body, headers={"Content-Disposition": "inline"})
