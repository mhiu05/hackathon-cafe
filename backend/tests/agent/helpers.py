# helpers.py
import json
def parse_sse(chunks: list[str]) -> list[tuple[str, dict]]:
    out = []
    for block in "".join(chunks).split("\n\n"):
        lines = [l for l in block.splitlines() if l and not l.startswith(":")]
        if lines:
            out.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return out
async def collect(gen) -> list[tuple[str, dict]]:
    return parse_sse([c async for c in gen])
