from typing import Any


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = [] if details is None else details


def not_found(resource: str) -> AppError:
    return AppError(404, "NOT_FOUND", f"{resource}不存在")

