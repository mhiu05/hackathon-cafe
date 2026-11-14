from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def sse_response(gen: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(gen, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def with_heartbeat(gen: AsyncIterator[str], interval_s: float = 15) -> AsyncIterator[str]:
    iterator = gen.__aiter__()
    pending = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(iterator))
            done, _ = await asyncio.wait({pending}, timeout=interval_s)
            if not done:
                yield ": ping\n\n"
                continue
            try:
                value = pending.result()
            except StopAsyncIteration:
                break
            pending = None
            yield value
    finally:
        if pending is not None:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await iterator.aclose()
