from typing import Dict, List, Optional

# Custom validation exceptions
class InvalidAuthenticationDataError(Exception):
    """Base exception for invalid data with support for multiple validation errors."""
    def __init__(self, message: str, errors: Optional[List[Dict[str, str]]] = None):
        self.errors = errors or []
        super().__init__(message)
        
class DatabaseConnectionError(InvalidAuthenticationDataError): pass
class UserAlreadyExistsError(InvalidAuthenticationDataError): pass
class UserNotFoundError(InvalidAuthenticationDataError): pass
class InvalidCredentialsError(InvalidAuthenticationDataError): pass


class InvalidRegestrationDataError(Exception):
    """Base exception for invalid data with support for multiple validation errors."""
    def __init__(self, message: str, errors: Optional[List[Dict[str, str]]] = None):
        self.errors = errors or []
        super().__init__(message)


class InvalidFirstNameError(InvalidRegestrationDataError):
    """Exception for invalid first name."""
    pass


class InvalidLastNameError(InvalidRegestrationDataError):
    """Exception for invalid last name."""
    pass


class InvalidEmailError(InvalidRegestrationDataError):
    """Exception for invalid email."""
    pass


class InvalidPhoneError(InvalidRegestrationDataError):
    """Exception for invalid phone number."""
    pass


class InvalidPasswordError(InvalidRegestrationDataError):
    """Exception for invalid password."""
    pass


class InvalidBirthDateError(InvalidRegestrationDataError):
    """Exception for invalid birth date."""
    pass



class InvalidAddressError(InvalidRegestrationDataError):
    """Exception for invalid address."""
    pass


class InvalidCityError(InvalidRegestrationDataError):
    """Exception for invalid city."""
    pass


class InvalidCountryError(InvalidRegestrationDataError):
    """Exception for invalid country."""
    pass