from __future__ import annotations

class APIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class AuthenticationError(APIError):
    pass


class NotFoundError(APIError):
    pass


class APIRateLimitError(APIError):
    pass
