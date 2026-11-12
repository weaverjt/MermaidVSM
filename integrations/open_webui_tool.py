"""
title: Mermaid Studio VSM Viewer
author: ILCJT
description: Renders a .vsm.json project (Mermaid + VSM metrics) in an embedded Mermaid Studio iframe.
requirements:
version: 1.1.0
"""

import base64
import html
import json
from typing import Any, Union

from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# allow-same-origin together with allow-scripts is only safe because Mermaid Studio is
# served from a DIFFERENT origin than Open WebUI. Never point `studio_url` at the
# Open WebUI origin itself with these flags, or the frame can escape its sandbox.
SANDBOX = "allow-scripts allow-same-origin allow-popups allow-forms allow-modals"


def encode_state(state: Union[dict, str]) -> str:
    """Compact JSON -> UTF-8 -> unpadded base64url (what Mermaid Studio's ?state= loader accepts)."""
    if isinstance(state, str):
        state = json.loads(state)
    raw = json.dumps(state, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class Tools:
    class Valves(BaseModel):
        studio_url: str = Field(
            default="https://weaverjt.github.io/MermaidVSM/src/mermaid_studio.html",
            description="Where Mermaid Studio is hosted (use the bundled build for internal hosting).",
        )
        iframe_height: int = Field(default=640, description="Iframe height in pixels.")
        max_url_chars: int = Field(
            default=7000,
            description="Above this URL length the state is delivered via postMessage instead of ?state=.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def open_vsm_studio(self, project_json: str) -> HTMLResponse:
        """
        Open a Value Stream Map / process flow in Mermaid Studio.
        :param project_json: A .vsm.json document as a JSON string ({"project":{...},"mermaid":"...","metrics":{...}}).
        """
        try:
            state: Any = json.loads(project_json)
            if not isinstance(state, dict) or not str(state.get("mermaid", "")).strip():
                raise ValueError('JSON must contain a non-empty "mermaid" field.')
        except Exception as exc:
            return HTMLResponse(
                content=f"<p>Invalid VSM JSON: {html.escape(str(exc))}</p>",
                headers={"Content-Disposition": "inline"},
            )

        url = f"{self.valves.studio_url}?state={encode_state(state)}"
        use_post_message = len(url) > self.valves.max_url_chars
        src = self.valves.studio_url if use_post_message else url

        script = ""
        if use_post_message:
            # Large diagrams exceed practical URL limits: wait for the app's vsm:ready, then push the state.
            payload = json.dumps(state).replace("</", "<\\/")
            script = (
                "<script>(function(){var f=document.getElementById('vsm');"
                f"var s={payload};"
                "window.addEventListener('message',function(e){"
                "if(e.source===f.contentWindow&&e.data&&e.data.type==='vsm:ready')"
                "f.contentWindow.postMessage({type:'vsm:load',state:s},'*');});})();</script>"
            )

        body = (
            '<iframe id="vsm" title="Mermaid Studio" '
            f'src="{html.escape(src, quote=True)}" sandbox="{SANDBOX}" '
            f'style="width:100%;height:{int(self.valves.iframe_height)}px;border:0;background:#020617"></iframe>'
            + script
        )
        return HTMLResponse(content=body, headers={"Content-Disposition": "inline"})
