class AccessDeniedError(Exception):
    """Exception raised when a user does not have permission to perform an action."""
    pass

class InvalidDataError(Exception):
    """Exception raised when invalid data is passed to variables or methods."""
    pass

class ItemNotFoundError(Exception):
    """Exception raised when a service, client, or product is not found."""
    pass
