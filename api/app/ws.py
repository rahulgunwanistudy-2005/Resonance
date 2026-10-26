import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.app.services.catalog import Catalog

router = APIRouter()


@router.websocket("/ws/live/{bridge_id}")
async def live(socket: WebSocket, bridge_id: str) -> None:
    await socket.accept()
    service: Catalog = socket.app.state.catalog
    previous = ""
    try:
        while True:
            records = await asyncio.to_thread(service.history, bridge_id)
            current = json.dumps(
                [
                    {
                        "id": item.capture.id,
                        "status": item.status,
                        "decision": item.result.decision.status
                        if item.result
                        else None,
                    }
                    for item in records[:20]
                ]
            )
            if current != previous:
                await socket.send_text(current)
                previous = current
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
