"""Dependency Injection container for Zero-ETL Lambda.

This module implements a simple IoC container that manages service
lifecycle and dependencies using factory functions.
"""

import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """Simple Dependency Injection container.

    Provides lazy instantiation and singleton scope for registered services.
    Services are registered as factory functions and instantiated on first access.

    Example:
        >>> container = ServiceContainer()
        >>> container.register("db", lambda c: DatabaseConnection(...))
        >>> db = container.resolve("db")  # DatabaseConnection instance
    """

    def __init__(self) -> None:
        """Initialize empty container."""
        self._factories: dict[str, Callable[["ServiceContainer"], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register(
        self,
        name: str,
        factory: Callable[["ServiceContainer"], T],
    ) -> None:
        """Register a service factory.

        Args:
            name: Unique service identifier.
            factory: Factory function that receives container and returns instance.
        """
        self._factories[name] = factory
        logger.debug("Registered service: %s", name)

    def resolve(self, name: str) -> Any:
        """Resolve and return a service instance.

        Services are lazily instantiated on first access and cached
        for subsequent calls (singleton scope).

        Args:
            name: Service identifier.

        Returns:
            Service instance.

        Raises:
            KeyError: If service is not registered.
        """
        if name not in self._instances:
            if name not in self._factories:
                raise KeyError(f"Service not registered: {name}")
            logger.debug("Instantiating service: %s", name)
            self._instances[name] = self._factories[name](self)
        return self._instances[name]

    def dispose(self) -> None:
        """Dispose all service instances.

        Calls close() method on instances that have it (e.g., database connections).
        """
        for name, instance in self._instances.items():
            if hasattr(instance, "close"):
                try:
                    instance.close()
                    logger.debug("Disposed service: %s", name)
                except Exception:
                    logger.exception("Error disposing service: %s", name)
        self._instances.clear()


def create_container() -> ServiceContainer:
    """Create and configure the DI container with all services.

    Reads configuration from environment variables and registers
    all required services for the ingestion pipeline.

    Returns:
        Configured ServiceContainer instance.
    """
    # Import here to avoid circular imports
    from api_client import APIClient
    from database import DatabaseConnection
    from processor import DataProcessor
    from service import ZeroETLService

    container = ServiceContainer()

    # Configuration from environment
    config = {
        "db_host": os.environ.get("DB_HOST", "localhost"),
        "db_port": int(os.environ.get("DB_PORT", "3306")),
        "db_name": os.environ.get("DB_NAME", "zero_etl_db"),
        "db_user": os.environ.get("DB_USER", "admin"),
        "db_password": os.environ.get("DB_PASSWORD", ""),
        "api_endpoint": os.environ.get(
            "API_ENDPOINT", "https://jsonplaceholder.typicode.com"
        ),
    }

    # Register configuration
    container.register("config", lambda _: config)

    # Register API client
    container.register(
        "api_client",
        lambda c: APIClient(base_url=c.resolve("config")["api_endpoint"]),
    )

    # Register database connection
    container.register(
        "database",
        lambda c: DatabaseConnection(
            host=c.resolve("config")["db_host"],
            port=c.resolve("config")["db_port"],
            database=c.resolve("config")["db_name"],
            user=c.resolve("config")["db_user"],
            password=c.resolve("config")["db_password"],
        ),
    )

    # Register data processor
    container.register(
        "processor",
        lambda _: DataProcessor(),
    )

    # Register Zero-ETL service (orchestrator)
    container.register(
        "zero_etl_service",
        lambda c: ZeroETLService(
            api_client=c.resolve("api_client"),
            database=c.resolve("database"),
            processor=c.resolve("processor"),
        ),
    )

    logger.info("Container configured with all services")
    return container
