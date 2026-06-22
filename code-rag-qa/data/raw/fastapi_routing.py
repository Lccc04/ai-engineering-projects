"""
FastAPI Routing Module (sample)
"""
from typing import List, Callable, Dict, Any, Optional


class Route:
    """Represents a single API route."""
    def __init__(self, path: str, endpoint: Callable, methods: List[str]):
        self.path = path
        self.endpoint = endpoint
        self.methods = methods


class APIRouter:
    """
    APIRouter is used to group path operations.
    A router can be included in a FastAPI app or another router.

    Examples:
        router = APIRouter(prefix="/users")
        router.add_api_route("/{user_id}", get_user, methods=["GET"])
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.routes: List[Route] = []

    def add_api_route(
        self,
        path: str,
        endpoint: Callable,
        methods: Optional[List[str]] = None,
    ) -> None:
        """
        Register an API route.

        Args:
            path: URL path
            endpoint: Handler function
            methods: HTTP methods, defaults to ["GET"]
        """
        if methods is None:
            methods = ["GET"]
        full_path = self.prefix + path
        route = Route(full_path, endpoint, methods)
        self.routes.append(route)

    def include_router(self, router: "APIRouter") -> None:
        """Include another router's routes with this router's prefix."""
        for route in router.routes:
            route.path = self.prefix + route.path
            self.routes.append(route)

    def get(self, path: str):
        """Decorator for GET routes."""
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["GET"])
            return func
        return decorator

    def post(self, path: str):
        """Decorator for POST routes."""
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["POST"])
            return func
        return decorator


class FastAPI:
    """
    Main FastAPI application class.

    Examples:
        app = FastAPI(title="My API", version="1.0.0")
        app.include_router(user_router)
    """

    def __init__(self, title: str = "FastAPI", version: str = "0.1.0"):
        self.title = title
        self.version = version
        self.routes: List[Route] = []
        self.middlewares: List[Callable] = []

    def include_router(self, router: APIRouter) -> None:
        """Add all routes from a router to the application."""
        self.routes.extend(router.routes)

    def add_middleware(self, middleware: Callable) -> None:
        """Register a middleware function."""
        self.middlewares.append(middleware)


# Dependency Injection
class Depends:
    """
    Declares a dependency for path operation functions.

    Usage:
        async def get_db():
            return Database()
        @app.get("/items")
        async def list_items(db = Depends(get_db)):
            return db.query(Item)
    """
    def __init__(self, dependency: Callable):
        self.dependency = dependency


async def get_current_user(token: str = "Bearer xxx"):
    """Dependency: extract current user from request token."""
    return {"username": "admin", "token": token}
