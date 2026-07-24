from __future__ import annotations

import logging

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=jsonable_encoder({
            "code": int(exc.code),
            "message": exc.message,
            "detail": exc.detail,
            "request_id": str(request.state.request_id),
        }),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({
            "code": int(ErrorCode.VALIDATION_FAILED),
            "message": "请求参数校验失败",
            "detail": exc.errors(),
            "request_id": str(request.state.request_id),
        }),
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled.request_error", extra={"request_id": request.state.request_id})
    return JSONResponse(
        status_code=500,
        content={
            "code": int(ErrorCode.INTERNAL_ERROR),
            "message": "内部服务错误",
            "detail": None,
            "request_id": str(request.state.request_id),
        },
    )
