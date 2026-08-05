from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

STATUS_CODES = {
    400: "bad_request",
    401: "authentication_required",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
}


def request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


async def http_exception_handler(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    detail = error.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or STATUS_CODES.get(error.status_code, "request_failed"))
        message = str(detail.get("message") or "The request could not be completed.")
        compatible_detail: Any = detail
    elif error.status_code >= 500:
        code = STATUS_CODES.get(error.status_code, "internal_error")
        message = "The service could not complete this request."
        compatible_detail = message
    else:
        code = STATUS_CODES.get(error.status_code, "request_failed")
        message = str(detail)
        compatible_detail = detail
    current_request_id = request_id(request)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": code,
            "message": message,
            "request_id": current_request_id,
            "detail": compatible_detail,
        },
        headers={"X-Request-ID": current_request_id, **(error.headers or {})},
    )


async def validation_exception_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    current_request_id = request_id(request)
    details = [
        {
            "location": list(item.get("loc", ())),
            "message": item.get("msg", "Invalid value"),
            "type": item.get("type", "value_error"),
        }
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "Check the submitted values and try again.",
            "request_id": current_request_id,
            "detail": details,
        },
        headers={"X-Request-ID": current_request_id},
    )


async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    current_request_id = request_id(request)
    logger.error(
        "Unhandled API error request_id=%s error_type=%s",
        current_request_id,
        type(error).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "The service could not complete this request.",
            "request_id": current_request_id,
            "detail": "The service could not complete this request.",
        },
        headers={"X-Request-ID": current_request_id},
    )
