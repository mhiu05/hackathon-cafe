from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        error = {"code": exc.code, "message": exc.message}
        if exc.details is not None:
            error["details"] = exc.details
        return JSONResponse({"error": error}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        malformed = any(e["type"] == "json_invalid" for e in exc.errors())
        return await api_error(request, ApiError(400 if malformed else 422,
            "BAD_REQUEST" if malformed else "VALIDATION_ERROR", "Dữ liệu không hợp lệ.",
            {"errors": [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]}))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return await api_error(request, ApiError(exc.status_code, "NOT_FOUND" if exc.status_code == 404 else "BAD_REQUEST", "Không tìm thấy tài nguyên."))

    @app.exception_handler(Exception)
    async def internal(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger(__name__).error("Unhandled backend error: %s", type(exc).__name__)
        return await api_error(request, ApiError(500, "INTERNAL", "Có lỗi hệ thống, vui lòng thử lại."))
