from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    message: str
    error_type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail

    @staticmethod
    def invalid_request(message: str, param: Optional[str] = None) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="invalid_request_error",
                param=param,
            )
        )

    @staticmethod
    def unauthorized(message: str) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="authentication_error",
            )
        )

    @staticmethod
    def not_found(message: str) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="not_found_error",
            )
        )

    @staticmethod
    def server_error(message: str) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="server_error",
            )
        )

    @staticmethod
    def rate_limit(message: str = "Rate limit exceeded") -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="rate_limit_error",
            )
        )

    def to_dict(self) -> dict:
        try:
            return self.model_dump()
        except AttributeError:
            return self.dict()
