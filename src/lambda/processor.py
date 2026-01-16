"""Data processor for transforming API responses to database records.

This module provides transformation logic from JSONPlaceholder API
response format to flattened database record format.
"""

import logging
from typing import Any

from models import Address, Comment, Company, GeoLocation, Post, User

logger = logging.getLogger(__name__)


class DataProcessor:
    """Transforms API responses to database-ready dictionaries.

    Handles flattening of nested JSON structures (address, company, geo)
    into flat column format suitable for MySQL tables.
    """

    def transform_user(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Transform raw user JSON to database record format.

        Flattens nested address and company objects into prefixed columns.

        Args:
            raw: Raw user dictionary from API.

        Returns:
            Flattened dictionary ready for database insert.
        """
        address = raw.get("address", {})
        geo = address.get("geo", {})
        company = raw.get("company", {})

        return {
            "id": raw["id"],
            "name": raw["name"],
            "username": raw["username"],
            "email": raw["email"],
            "phone": raw.get("phone"),
            "website": raw.get("website"),
            "address_street": address.get("street"),
            "address_suite": address.get("suite"),
            "address_city": address.get("city"),
            "address_zipcode": address.get("zipcode"),
            "address_geo_lat": float(geo["lat"]) if geo.get("lat") else None,
            "address_geo_lng": float(geo["lng"]) if geo.get("lng") else None,
            "company_name": company.get("name"),
            "company_catch_phrase": company.get("catchPhrase"),
            "company_bs": company.get("bs"),
        }

    def transform_users(self, raw_users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform list of raw users to database records.

        Args:
            raw_users: List of raw user dictionaries from API.

        Returns:
            List of flattened dictionaries ready for database insert.
        """
        result = [self.transform_user(u) for u in raw_users]
        logger.info("Transformed %d users", len(result))
        return result

    def transform_post(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Transform raw post JSON to database record format.

        Args:
            raw: Raw post dictionary from API.

        Returns:
            Dictionary ready for database insert.
        """
        return {
            "id": raw["id"],
            "user_id": raw["userId"],
            "title": raw["title"],
            "body": raw["body"],
        }

    def transform_posts(self, raw_posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform list of raw posts to database records.

        Args:
            raw_posts: List of raw post dictionaries from API.

        Returns:
            List of dictionaries ready for database insert.
        """
        result = [self.transform_post(p) for p in raw_posts]
        logger.info("Transformed %d posts", len(result))
        return result

    def transform_comment(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Transform raw comment JSON to database record format.

        Args:
            raw: Raw comment dictionary from API.

        Returns:
            Dictionary ready for database insert.
        """
        return {
            "id": raw["id"],
            "post_id": raw["postId"],
            "name": raw["name"],
            "email": raw["email"],
            "body": raw["body"],
        }

    def transform_comments(
        self, raw_comments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform list of raw comments to database records.

        Args:
            raw_comments: List of raw comment dictionaries from API.

        Returns:
            List of dictionaries ready for database insert.
        """
        result = [self.transform_comment(c) for c in raw_comments]
        logger.info("Transformed %d comments", len(result))
        return result

    def to_user_model(self, raw: dict[str, Any]) -> User:
        """Convert raw user JSON to User dataclass.

        Args:
            raw: Raw user dictionary from API.

        Returns:
            User dataclass instance.
        """
        address_raw = raw.get("address", {})
        geo_raw = address_raw.get("geo", {})
        company_raw = raw.get("company", {})

        geo = None
        if geo_raw:
            geo = GeoLocation(
                lat=float(geo_raw["lat"]),
                lng=float(geo_raw["lng"]),
            )

        address = None
        if address_raw:
            address = Address(
                street=address_raw.get("street", ""),
                suite=address_raw.get("suite", ""),
                city=address_raw.get("city", ""),
                zipcode=address_raw.get("zipcode", ""),
                geo=geo,
            )

        company = None
        if company_raw:
            company = Company(
                name=company_raw.get("name", ""),
                catch_phrase=company_raw.get("catchPhrase", ""),
                bs=company_raw.get("bs", ""),
            )

        return User(
            id=raw["id"],
            name=raw["name"],
            username=raw["username"],
            email=raw["email"],
            phone=raw.get("phone"),
            website=raw.get("website"),
            address=address,
            company=company,
        )

    def to_post_model(self, raw: dict[str, Any]) -> Post:
        """Convert raw post JSON to Post dataclass.

        Args:
            raw: Raw post dictionary from API.

        Returns:
            Post dataclass instance.
        """
        return Post(
            id=raw["id"],
            user_id=raw["userId"],
            title=raw["title"],
            body=raw["body"],
        )

    def to_comment_model(self, raw: dict[str, Any]) -> Comment:
        """Convert raw comment JSON to Comment dataclass.

        Args:
            raw: Raw comment dictionary from API.

        Returns:
            Comment dataclass instance.
        """
        return Comment(
            id=raw["id"],
            post_id=raw["postId"],
            name=raw["name"],
            email=raw["email"],
            body=raw["body"],
        )
