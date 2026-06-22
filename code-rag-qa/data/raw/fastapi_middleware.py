"""
FastAPI Exception Handling and Middleware
"""
from typing import Callable, Dict, Any


class HTTPException(Exception):
    """
    HTTP exception that can be raised to return specific HTTP responses.

    Usage:
        raise HTTPException(status_code=404, detail="Item not found")
    """
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class Request:
    """Represents an incoming HTTP request."""
    def __init__(self, method: str, url: str, headers: Dict[str, str], body: Any = None):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    @property
    def path_params(self) -> Dict[str, str]:
        """Extract path parameters from URL."""
        return {}


class Response:
    """Represents an HTTP response."""
    def __init__(self, content: Any, status_code: int = 200, headers: Dict[str, str] = None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}


class MiddlewareManager:
    """
    Manages request/response middleware pipeline.

    Middleware wraps around each request, allowing pre-processing
    and post-processing of requests and responses.
    """

    def __init__(self):
        self._middlewares: list = []

    def add(self, middleware: Callable) -> None:
        """Register a middleware in the pipeline."""
        self._middlewares.append(middleware)

    async def dispatch(self, request: Request) -> Response:
        """Run the request through all middleware."""
        response = Response(None)
        for mw in self._middlewares:
            response = await mw(request, response) if hasattr(mw, '__call__') else mw(request)
        return response


class ExceptionHandler:
    """
    Global exception handler registry.

    Usage:
        app.add_exception_handler(404, custom_404_handler)
        app.add_exception_handler(ValueError, value_error_handler)
    """

    def __init__(self):
        self._handlers: Dict[int, Callable] = {}
        self._type_handlers: Dict[type, Callable] = {}

    def register(self, exc_or_code, handler: Callable) -> None:
        """Register an exception handler."""
        if isinstance(exc_or_code, int):
            self._handlers[exc_or_code] = handler
        else:
            self._type_handlers[exc_or_code] = handler

    def handle(self, exception: Exception) -> Response:
        """Find and invoke the appropriate handler."""
        if isinstance(exception, HTTPException):
            if exception.status_code in self._handlers:
                return self._handlers[exception.status_code](exception)
            return Response(
                content={"detail": exception.detail},
                status_code=exception.status_code,
            )
        for exc_type, handler in self._type_handlers.items():
            if isinstance(exception, exc_type):
                return handler(exception)
        return Response(content={"detail": "Internal server error"}, status_code=500)
