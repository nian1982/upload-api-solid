class WSError(Exception):
    def __init__(self, message: str, original: Exception | None = None):
        self.message = message
        self.original = original
        super().__init__(message)


class WSPublishError(WSError):
    pass


class WSSubscriptionError(WSError):
    pass
