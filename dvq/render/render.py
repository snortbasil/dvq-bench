"""Python wrapper over the Node/Playwright D3 renderer. Returns a base64 PNG, or
None if rendering is unavailable (Node or the browser not installed) so the run
loop degrades to the deterministic tier rather than crashing."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ..schemas import ChartSpec, DataRow

_SCRIPT = Path(__file__).parent / "render.mjs"


async def render_png(spec: ChartSpec, data: list[DataRow] | None = None, width: int = 720, height: int = 460) -> str | None:
    payload = json.dumps({
        "code": spec.d3_code,
        "data": [d.model_dump() for d in (data or [])],
        "width": width,
        "height": height,
    })
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", str(_SCRIPT),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate(payload.encode())
    except FileNotFoundError:
        return None  # node not installed
    if proc.returncode != 0 or not out:
        return None
    return out.decode().strip()
