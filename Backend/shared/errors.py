"""Application errors independent of the HTTP transport."""


class ApplicationError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


class AuthError(ApplicationError):
    pass


class IngestaError(ApplicationError):
    pass
