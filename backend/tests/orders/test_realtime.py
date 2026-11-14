import asyncio
from app.realtime.bus import EventBus
from app.realtime.sse import with_heartbeat

async def test_bus_drops_oldest_and_unsubscribes():
    bus = EventBus()
    async with bus.subscribe("admin") as stream:
        for i in range(101):
            bus.publish("admin", "order_created", {"id": i})
        assert await anext(stream) == ("order_created", {"id": 1})
    bus.publish("admin", "order_created", {"id": 999})
    async with bus.subscribe("admin") as stream:
        bus.publish("admin", "order_updated", {"id": 2})
        assert await anext(stream) == ("order_updated", {"id": 2})

async def test_heartbeat_does_not_cancel_pending_event():
    ready = asyncio.Event()
    async def source():
        await ready.wait()
        yield "data event"
    stream = with_heartbeat(source(), interval_s=.01)
    assert await anext(stream) == ": ping\n\n"
    ready.set()
    assert await anext(stream) == "data event"
    await stream.aclose()
