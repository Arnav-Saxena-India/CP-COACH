"""
Structured Error Response Module for CP Coach.

Provides consistent error handling and response formatting.
All API errors should use these structures.
"""

from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    
    # Client errors (4xx)
    INVALID_HANDLE = "INVALID_HANDLE"
    HANDLE_NOT_FOUND = "HANDLE_NOT_FOUND"
    INVALID_TOPIC = "INVALID_TOPIC"
    INVALID_REQUEST = "INVALID_REQUEST"
    RATE_LIMITED = "RATE_LIMITED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Server errors (5xx)
    CF_API_ERROR = "CF_API_ERROR"
    CF_API_TIMEOUT = "CF_API_TIMEOUT"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass
class ErrorResponse:
    """Structured error response for API endpoints."""
    
    error: bool
    code: str
    message: str
    detail: Optional[str] = None
    timestamp: str = None
    retry_after: Optional[int] = None  # For rate limiting
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "error": self.error,
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp
        }
        if self.detail:
            result["detail"] = self.detail
        if self.retry_after:
            result["retry_after"] = self.retry_after
        return result


class APIError(Exception):
    """Base exception for API errors with structured response."""
    
    def __init__(
        self, 
        code: ErrorCode, 
        message: str, 
        status_code: int = 400,
        detail: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after
        super().__init__(message)
    
    def to_response(self) -> ErrorResponse:
        """Convert to ErrorResponse."""
        return ErrorResponse(
            error=True,
            code=self.code.value,
            message=self.message,
            detail=self.detail,
            retry_after=self.retry_after
        )


# Specific error classes for common scenarios
class InvalidHandleError(APIError):
    """Raised when CF handle format is invalid."""
    
    def __init__(self, handle: str):
        super().__init__(
            code=ErrorCode.INVALID_HANDLE,
            message=f"Invalid Codeforces handle format: '{handle}'",
            status_code=400,
            detail="Handle must be 3-24 characters, alphanumeric with _ or -"
        )


class HandleNotFoundError(APIError):
    """Raised when CF handle doesn't exist."""
    
    def __init__(self, handle: str):
        super().__init__(
            code=ErrorCode.HANDLE_NOT_FOUND,
            message=f"Codeforces handle not found: '{handle}'",
            status_code=404,
            detail="The handle does not exist on Codeforces"
        )


class CFAPIError(APIError):
    """Raised when Codeforces API fails."""
    
    def __init__(self, message: str = "Codeforces API error", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.CF_API_ERROR,
            message=message,
            status_code=502,
            detail=detail
        )


class CFAPITimeoutError(APIError):
    """Raised when Codeforces API times out."""
    
    def __init__(self):
        super().__init__(
            code=ErrorCode.CF_API_TIMEOUT,
            message="Codeforces API timeout",
            status_code=504,
            detail="The Codeforces API did not respond in time. Please try again."
        )


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message="Rate limit exceeded",
            status_code=429,
            detail="Too many requests. Please slow down.",
            retry_after=retry_after
        )


class ValidationError(APIError):
    """Raised for request validation failures."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=400,
            detail=detail
        )


# Helper functions for creating standard responses
def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Create a standard success response."""
    response = {
        "error": False,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if message:
        response["message"] = message
    return response


def empty_response(message: str = "No data found") -> Dict[str, Any]:
    """Create a standard empty response (not an error)."""
    return {
        "error": False,
        "data": [],
        "message": message,
        "empty": True,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
