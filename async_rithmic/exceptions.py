class RithmicErrorResponse(Exception):
    """Raised when Rithmic returns an error."""
    pass


class InvalidRequestError(Exception):
    """Raised when a user-level API call is missing required arguments or is malformed."""
    pass

class HistoricalDataRequestInProgressError(RuntimeError):
    pass


class HistoricalDataPaginationError(RuntimeError):
    """Raised when historical data cannot be paginated without losing data."""
    pass


class HistoricalDataIncompleteError(RuntimeError):
    """Raised when a historical request reaches its page limit incomplete."""
    pass


class HistoricalDataConnectionError(RuntimeError):
    """Raised when a historical request is interrupted by a connection loss."""
    pass
