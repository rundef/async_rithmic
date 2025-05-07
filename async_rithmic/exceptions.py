class RithmicErrorResponse(Exception):
    """Raised when Rithmic returns an error."""
    pass


class InvalidRequestError(Exception):
    """Raised when a user-level API call is missing required arguments or is malformed."""
    pass
