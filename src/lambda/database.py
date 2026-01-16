"""Database connection manager for Aurora MySQL.

This module provides connection management, batch operations,
and transaction handling for MySQL database.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Exception raised for database errors."""

    pass


class DatabaseConnection:
    """MySQL database connection manager.

    Provides connection pooling, context managers for transactions,
    and batch insert operations with rollback on failure.

    Attributes:
        host: Database host address.
        port: Database port.
        database: Database name.
        user: Database username.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        pool_size: int = 5,
    ) -> None:
        """Initialize database connection manager.

        Args:
            host: Database host address.
            port: Database port number.
            database: Database name.
            user: Database username.
            password: Database password.
            pool_size: Connection pool size.
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self._password = password
        self._pool_size = pool_size
        self._connection: Optional[MySQLConnection] = None
        logger.info(
            "DatabaseConnection initialized: host=%s, port=%s, database=%s",
            host,
            port,
            database,
        )

    def _get_connection(self) -> MySQLConnection:
        """Get or create database connection.

        Returns:
            Active MySQL connection.

        Raises:
            DatabaseError: If connection fails.
        """
        if self._connection is None or not self._connection.is_connected():
            try:
                self._connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self._password,
                    autocommit=False,
                    charset="utf8mb4",
                    collation="utf8mb4_unicode_ci",
                    connection_timeout=30,
                )
                logger.info("Database connection established")
            except MySQLError as e:
                logger.error("Failed to connect to database: %s", e)
                raise DatabaseError(f"Connection failed: {e}") from e
        return self._connection

    @contextmanager
    def transaction(self) -> Generator[MySQLCursor, None, None]:
        """Context manager for database transactions.

        Automatically commits on success, rolls back on exception.

        Yields:
            MySQL cursor for executing queries.

        Raises:
            DatabaseError: If transaction fails.
        """
        connection = self._get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
            logger.debug("Transaction committed")
        except Exception as e:
            connection.rollback()
            logger.error("Transaction rolled back due to error: %s", e)
            raise
        finally:
            cursor.close()

    def batch_upsert_users(
        self,
        cursor: MySQLCursor,
        users: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Batch upsert users with INSERT ... ON DUPLICATE KEY UPDATE.

        Args:
            cursor: Active MySQL cursor.
            users: List of user dictionaries to insert/update.

        Returns:
            Tuple of (inserted_count, updated_count).

        Raises:
            DatabaseError: If operation fails.
        """
        if not users:
            return 0, 0

        sql = """
            INSERT INTO users (
                id, name, username, email, phone, website,
                address_street, address_suite, address_city, address_zipcode,
                address_geo_lat, address_geo_lng,
                company_name, company_catch_phrase, company_bs
            ) VALUES (
                %(id)s, %(name)s, %(username)s, %(email)s, %(phone)s, %(website)s,
                %(address_street)s, %(address_suite)s, %(address_city)s, %(address_zipcode)s,
                %(address_geo_lat)s, %(address_geo_lng)s,
                %(company_name)s, %(company_catch_phrase)s, %(company_bs)s
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                username = VALUES(username),
                email = VALUES(email),
                phone = VALUES(phone),
                website = VALUES(website),
                address_street = VALUES(address_street),
                address_suite = VALUES(address_suite),
                address_city = VALUES(address_city),
                address_zipcode = VALUES(address_zipcode),
                address_geo_lat = VALUES(address_geo_lat),
                address_geo_lng = VALUES(address_geo_lng),
                company_name = VALUES(company_name),
                company_catch_phrase = VALUES(company_catch_phrase),
                company_bs = VALUES(company_bs)
        """

        try:
            cursor.executemany(sql, users)
            affected_rows = cursor.rowcount
            # MySQL returns 1 for insert, 2 for update on duplicate key
            # This is an approximation
            inserted = len(users)
            updated = affected_rows - inserted if affected_rows > inserted else 0
            logger.info(
                "Users upserted: %d records, %d affected rows",
                len(users),
                affected_rows,
            )
            return inserted, updated
        except MySQLError as e:
            logger.error("Failed to upsert users: %s", e)
            raise DatabaseError(f"Batch upsert users failed: {e}") from e

    def batch_upsert_posts(
        self,
        cursor: MySQLCursor,
        posts: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Batch upsert posts with INSERT ... ON DUPLICATE KEY UPDATE.

        Args:
            cursor: Active MySQL cursor.
            posts: List of post dictionaries to insert/update.

        Returns:
            Tuple of (inserted_count, updated_count).

        Raises:
            DatabaseError: If operation fails.
        """
        if not posts:
            return 0, 0

        sql = """
            INSERT INTO posts (id, user_id, title, body)
            VALUES (%(id)s, %(user_id)s, %(title)s, %(body)s)
            ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                title = VALUES(title),
                body = VALUES(body)
        """

        try:
            cursor.executemany(sql, posts)
            affected_rows = cursor.rowcount
            inserted = len(posts)
            updated = affected_rows - inserted if affected_rows > inserted else 0
            logger.info(
                "Posts upserted: %d records, %d affected rows",
                len(posts),
                affected_rows,
            )
            return inserted, updated
        except MySQLError as e:
            logger.error("Failed to upsert posts: %s", e)
            raise DatabaseError(f"Batch upsert posts failed: {e}") from e

    def batch_upsert_comments(
        self,
        cursor: MySQLCursor,
        comments: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Batch upsert comments with INSERT ... ON DUPLICATE KEY UPDATE.

        Args:
            cursor: Active MySQL cursor.
            comments: List of comment dictionaries to insert/update.

        Returns:
            Tuple of (inserted_count, updated_count).

        Raises:
            DatabaseError: If operation fails.
        """
        if not comments:
            return 0, 0

        sql = """
            INSERT INTO comments (id, post_id, name, email, body)
            VALUES (%(id)s, %(post_id)s, %(name)s, %(email)s, %(body)s)
            ON DUPLICATE KEY UPDATE
                post_id = VALUES(post_id),
                name = VALUES(name),
                email = VALUES(email),
                body = VALUES(body)
        """

        try:
            cursor.executemany(sql, comments)
            affected_rows = cursor.rowcount
            inserted = len(comments)
            updated = affected_rows - inserted if affected_rows > inserted else 0
            logger.info(
                "Comments upserted: %d records, %d affected rows",
                len(comments),
                affected_rows,
            )
            return inserted, updated
        except MySQLError as e:
            logger.error("Failed to upsert comments: %s", e)
            raise DatabaseError(f"Batch upsert comments failed: {e}") from e

    def log_ingestion(
        self,
        cursor: MySQLCursor,
        run_id: str,
        entity_type: str,
        records_fetched: int,
        records_inserted: int,
        records_updated: int,
        status: str,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Log ingestion operation to ingestion_log table.

        Args:
            cursor: Active MySQL cursor.
            run_id: Unique run identifier.
            entity_type: Type of entity (users, posts, comments).
            records_fetched: Number of records fetched.
            records_inserted: Number of records inserted.
            records_updated: Number of records updated.
            status: Operation status (started, success, failed).
            error_message: Error message if failed.
            duration_ms: Operation duration in milliseconds.
        """
        sql = """
            INSERT INTO ingestion_log (
                run_id, entity_type, records_fetched, records_inserted,
                records_updated, status, error_message, duration_ms,
                completed_at
            ) VALUES (
                %(run_id)s, %(entity_type)s, %(records_fetched)s, %(records_inserted)s,
                %(records_updated)s, %(status)s, %(error_message)s, %(duration_ms)s,
                CASE WHEN %(status)s != 'started' THEN CURRENT_TIMESTAMP ELSE NULL END
            )
        """

        try:
            cursor.execute(
                sql,
                {
                    "run_id": run_id,
                    "entity_type": entity_type,
                    "records_fetched": records_fetched,
                    "records_inserted": records_inserted,
                    "records_updated": records_updated,
                    "status": status,
                    "error_message": error_message,
                    "duration_ms": duration_ms,
                },
            )
            logger.debug(
                "Logged ingestion: run_id=%s, entity=%s, status=%s",
                run_id,
                entity_type,
                status,
            )
        except MySQLError as e:
            # Don't raise on logging failure, just log the error
            logger.error("Failed to log ingestion: %s", e)

    def close(self) -> None:
        """Close database connection."""
        if self._connection is not None and self._connection.is_connected():
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
