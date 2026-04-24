from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.schemas.chat import ChatHistoryResponse, ChatListResponse, ChatRequest, ChatResponse, RenameRequest
from app.services.chat_service import ChatService, ChatServiceError

router = APIRouter()
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(payload: ChatRequest):
    try:
        return await chat_service.process_chat(payload)
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error.",
        ) from exc


@router.get("/chat/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    try:
        return await chat_service.get_history(session_id)
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/chats", response_model=ChatListResponse)
async def list_chats():
    try:
        return await chat_service.list_chats()
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/chat/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(session_id: str):
    try:
        await chat_service.delete_chat(session_id)
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/chat/{session_id}/rename", status_code=status.HTTP_200_OK)
async def rename_chat(session_id: str, payload: RenameRequest):
    try:
        await chat_service.rename_chat(session_id, payload.title)
        return {"session_id": session_id, "title": payload.title}
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/admin/pending", response_model=ChatListResponse)
async def list_pending_admin():
    try:
        return await chat_service.list_pending_admin()
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/admin/resolved", response_model=ChatListResponse)
async def list_resolved_admin():
    try:
        return await chat_service.list_resolved_admin()
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/admin/answer/{session_id}", status_code=status.HTTP_200_OK)
async def answer_as_admin(session_id: str, payload: ChatRequest):
    try:
        await chat_service.answer_as_admin(session_id, payload.message)
        return {"status": "success"}
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/admin/close/{session_id}", status_code=status.HTTP_200_OK)
async def close_ticket(session_id: str):
    try:
        await chat_service.close_ticket(session_id)
        return {"status": "success"}
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/chat/{session_id}/support", status_code=status.HTTP_200_OK)
async def add_support_message(session_id: str, payload: ChatRequest):
    try:
        await chat_service.add_support_message(session_id, payload.message, payload.user_name)
        return {"status": "success"}
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/chat/{session_id}/support")
async def get_support_messages(session_id: str):
    try:
        return await chat_service.get_support_messages(session_id)
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.websocket("/ws/chat/{session_id}")
async def chat_socket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()
            message = (payload.get("message") or "").strip()

            if not message:
                await websocket.send_json({"type": "error", "detail": "Message cannot be empty."})
                continue

            try:
                async for chunk in chat_service.stream_chat(
                    ChatRequest(session_id=session_id, message=message)
                ):
                    await websocket.send_json(chunk)
            except ChatServiceError as exc:
                await websocket.send_json({"type": "error", "detail": exc.message})
    except WebSocketDisconnect:
        return
