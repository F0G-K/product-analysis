"""聊天 SSE API：流式对话接口。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天"])


class ChatStreamRequest(BaseModel):
    conversation_id: str | None = Field(default=None, description="对话 ID，首次为空则创建新对话")
    task_id: str | None = Field(default=None, description="关联的任务 ID，用于注入任务上下文")
    message: str = Field(..., min_length=1, description="用户消息")
    provider: str = Field(default="", description="LLM provider 名称")
    model: str = Field(default="", description="模型名称")


class ConversationSummary(BaseModel):
    id: str
    task_id: str | None
    message_count: int
    first_message: str
    created_at: str


@router.post("/stream")
async def chat_stream(req: ChatStreamRequest, request: Request):
    """SSE 流式聊天端点。"""
    chat_service: ChatService = request.app.state.chat_service

    async def event_generator():
        try:
            async for chunk in chat_service.chat_stream(
                conversation_id=req.conversation_id,
                task_id=req.task_id,
                message=req.message,
                provider_name=req.provider,
                model_name=req.model,
            ):
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"
            # 发送完成信号，附带 conversation_id
            conv_id = req.conversation_id
            if not conv_id:
                # 从最近创建的对话中获取
                conversations = chat_service.list_conversations()
                if conversations:
                    conv_id = conversations[0]["id"]
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("chat.sse_error")
            yield f"data: {json.dumps({'type': 'error', 'content': '服务异常，请稍后重试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations(request: Request) -> list[ConversationSummary]:
    chat_service: ChatService = request.app.state.chat_service
    conversations = chat_service.list_conversations()
    return [
        ConversationSummary(
            id=c["id"],
            task_id=c.get("task_id"),
            message_count=len(c.get("messages", [])),
            first_message=c["messages"][0]["content"][:80] if c.get("messages") else "",
            created_at=c.get("created_at", ""),
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request):
    chat_service: ChatService = request.app.state.chat_service
    conv = chat_service.get_conversation(conversation_id)
    if conv is None:
        return {"code": 404, "message": "对话不存在"}
    return {
        "id": conv["id"],
        "task_id": conv.get("task_id"),
        "messages": conv.get("messages", []),
        "created_at": conv.get("created_at", ""),
    }
