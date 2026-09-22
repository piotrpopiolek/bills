class AppError(Exception):
    """Base class for all application exceptions."""

    pass


class ResourceNotFoundError(AppError):
    """Generic error when a requested resource is not found."""

    def __init__(self, resource_name: str, identifier: any):
        self.message = f"{resource_name} z identyfikatorem {identifier} nie znaleziono."
        super().__init__(self.message)


class ResourceAlreadyExistsError(AppError):
    def __init__(self, resource_name: str, field: str, value: any):
        self.message = f"{resource_name} z {field} '{value}' już istnieje."
        super().__init__(self.message)


class UserCreationError(AppError):
    """Error when user creation fails for reasons other than duplicate."""

    def __init__(self, reason: str):
        self.message = f"Nie udało się utworzyć użytkownika: {reason}"
        self.reason = reason
        super().__init__(self.message)


class BillAccessDeniedError(AppError):
    """Error when user tries to access a bill that doesn't belong to them."""

    def __init__(self, bill_id: int):
        self.message = f"Paragon z identyfikatorem {bill_id} nie znaleziono."
        self.bill_id = bill_id
        super().__init__(self.message)
