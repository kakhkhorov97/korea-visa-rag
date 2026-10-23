"""Safe provider failures shared by interfaces without importing an SDK."""


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code
