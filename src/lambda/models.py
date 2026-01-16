"""Data models for Zero-ETL ingestion pipeline.

This module defines dataclasses representing entities fetched from
JSONPlaceholder API and stored in Aurora MySQL.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class GeoLocation:
    """Geographic coordinates."""

    lat: float
    lng: float


@dataclass(frozen=True, slots=True)
class Address:
    """User address information."""

    street: str
    suite: str
    city: str
    zipcode: str
    geo: Optional[GeoLocation] = None


@dataclass(frozen=True, slots=True)
class Company:
    """User company information."""

    name: str
    catch_phrase: str
    bs: str


@dataclass(frozen=True, slots=True)
class User:
    """User entity from JSONPlaceholder /users endpoint.

    Attributes:
        id: Unique user identifier.
        name: Full name of the user.
        username: Unique username.
        email: Email address.
        phone: Phone number (optional).
        website: Website URL (optional).
        address: Address information (optional).
        company: Company information (optional).
    """

    id: int
    name: str
    username: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[Address] = None
    company: Optional[Company] = None


@dataclass(frozen=True, slots=True)
class Post:
    """Post entity from JSONPlaceholder /posts endpoint.

    Attributes:
        id: Unique post identifier.
        user_id: Reference to the user who created the post.
        title: Post title.
        body: Post content.
    """

    id: int
    user_id: int
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class Comment:
    """Comment entity from JSONPlaceholder /comments endpoint.

    Attributes:
        id: Unique comment identifier.
        post_id: Reference to the parent post.
        name: Comment title/name.
        email: Email of the commenter.
        body: Comment content.
    """

    id: int
    post_id: int
    name: str
    email: str
    body: str


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Result of an ingestion operation.

    Attributes:
        entity_type: Type of entity ingested (users, posts, comments).
        records_fetched: Number of records fetched from API.
        records_inserted: Number of records inserted.
        records_updated: Number of records updated.
        duration_ms: Duration of the operation in milliseconds.
        success: Whether the operation succeeded.
        error_message: Error message if operation failed.
    """

    entity_type: str
    records_fetched: int
    records_inserted: int
    records_updated: int
    duration_ms: int
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    """Summary of a complete ingestion run.

    Attributes:
        run_id: Unique identifier for this run.
        started_at: When the run started.
        completed_at: When the run completed.
        results: List of ingestion results per entity type.
        total_records: Total number of records processed.
        success: Whether all operations succeeded.
    """

    run_id: str
    started_at: datetime
    completed_at: datetime
    results: list[IngestionResult]
    total_records: int
    success: bool
