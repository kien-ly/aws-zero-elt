"""Zero-ETL ingestion service orchestrator.

This module provides the main orchestration logic for the ingestion
pipeline: fetch from API -> transform -> batch insert to database.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from models import IngestionResult, IngestionSummary

if TYPE_CHECKING:
    from api_client import APIClient
    from database import DatabaseConnection
    from processor import DataProcessor

logger = logging.getLogger(__name__)


class ZeroETLService:
    """Orchestrates the Zero-ETL ingestion pipeline.

    Coordinates fetching data from JSONPlaceholder API, transforming it,
    and batch inserting into Aurora MySQL. Handles error logging and
    transaction management.

    Attributes:
        api_client: HTTP client for JSONPlaceholder API.
        database: Database connection manager.
        processor: Data transformation processor.
    """

    def __init__(
        self,
        api_client: "APIClient",
        database: "DatabaseConnection",
        processor: "DataProcessor",
    ) -> None:
        """Initialize Zero-ETL service.

        Args:
            api_client: HTTP client for API calls.
            database: Database connection manager.
            processor: Data transformation processor.
        """
        self.api_client = api_client
        self.database = database
        self.processor = processor
        logger.info("ZeroETLService initialized")

    def ingest_users(self, run_id: str) -> IngestionResult:
        """Ingest users from API to database.

        Fetches all users from /users endpoint, transforms them,
        and batch upserts to users table.

        Args:
            run_id: Unique identifier for this ingestion run.

        Returns:
            IngestionResult with operation statistics.
        """
        entity_type = "users"
        start_time = time.time()
        logger.info("Starting users ingestion, run_id=%s", run_id)

        try:
            # Fetch from API
            raw_users = self.api_client.fetch_users()
            records_fetched = len(raw_users)

            # Transform data
            db_records = self.processor.transform_users(raw_users)

            # Batch insert with transaction
            with self.database.transaction() as cursor:
                inserted, updated = self.database.batch_upsert_users(cursor, db_records)

                # Log success
                duration_ms = int((time.time() - start_time) * 1000)
                self.database.log_ingestion(
                    cursor=cursor,
                    run_id=run_id,
                    entity_type=entity_type,
                    records_fetched=records_fetched,
                    records_inserted=inserted,
                    records_updated=updated,
                    status="success",
                    duration_ms=duration_ms,
                )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Users ingestion completed: fetched=%d, inserted=%d, updated=%d, duration=%dms",
                records_fetched,
                inserted,
                updated,
                duration_ms,
            )

            return IngestionResult(
                entity_type=entity_type,
                records_fetched=records_fetched,
                records_inserted=inserted,
                records_updated=updated,
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error("Users ingestion failed: %s", error_msg)

            # Log failure (in a new transaction)
            try:
                with self.database.transaction() as cursor:
                    self.database.log_ingestion(
                        cursor=cursor,
                        run_id=run_id,
                        entity_type=entity_type,
                        records_fetched=0,
                        records_inserted=0,
                        records_updated=0,
                        status="failed",
                        error_message=error_msg,
                        duration_ms=duration_ms,
                    )
            except Exception:
                logger.exception("Failed to log ingestion failure")

            return IngestionResult(
                entity_type=entity_type,
                records_fetched=0,
                records_inserted=0,
                records_updated=0,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )

    def ingest_posts(self, run_id: str) -> IngestionResult:
        """Ingest posts from API to database.

        Fetches all posts from /posts endpoint, transforms them,
        and batch upserts to posts table.

        Args:
            run_id: Unique identifier for this ingestion run.

        Returns:
            IngestionResult with operation statistics.
        """
        entity_type = "posts"
        start_time = time.time()
        logger.info("Starting posts ingestion, run_id=%s", run_id)

        try:
            # Fetch from API
            raw_posts = self.api_client.fetch_posts()
            records_fetched = len(raw_posts)

            # Transform data
            db_records = self.processor.transform_posts(raw_posts)

            # Batch insert with transaction
            with self.database.transaction() as cursor:
                inserted, updated = self.database.batch_upsert_posts(cursor, db_records)

                # Log success
                duration_ms = int((time.time() - start_time) * 1000)
                self.database.log_ingestion(
                    cursor=cursor,
                    run_id=run_id,
                    entity_type=entity_type,
                    records_fetched=records_fetched,
                    records_inserted=inserted,
                    records_updated=updated,
                    status="success",
                    duration_ms=duration_ms,
                )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Posts ingestion completed: fetched=%d, inserted=%d, updated=%d, duration=%dms",
                records_fetched,
                inserted,
                updated,
                duration_ms,
            )

            return IngestionResult(
                entity_type=entity_type,
                records_fetched=records_fetched,
                records_inserted=inserted,
                records_updated=updated,
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error("Posts ingestion failed: %s", error_msg)

            try:
                with self.database.transaction() as cursor:
                    self.database.log_ingestion(
                        cursor=cursor,
                        run_id=run_id,
                        entity_type=entity_type,
                        records_fetched=0,
                        records_inserted=0,
                        records_updated=0,
                        status="failed",
                        error_message=error_msg,
                        duration_ms=duration_ms,
                    )
            except Exception:
                logger.exception("Failed to log ingestion failure")

            return IngestionResult(
                entity_type=entity_type,
                records_fetched=0,
                records_inserted=0,
                records_updated=0,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )

    def ingest_comments(self, run_id: str) -> IngestionResult:
        """Ingest comments from API to database.

        Fetches all comments from /comments endpoint, transforms them,
        and batch upserts to comments table.

        Args:
            run_id: Unique identifier for this ingestion run.

        Returns:
            IngestionResult with operation statistics.
        """
        entity_type = "comments"
        start_time = time.time()
        logger.info("Starting comments ingestion, run_id=%s", run_id)

        try:
            # Fetch from API
            raw_comments = self.api_client.fetch_comments()
            records_fetched = len(raw_comments)

            # Transform data
            db_records = self.processor.transform_comments(raw_comments)

            # Batch insert with transaction
            with self.database.transaction() as cursor:
                inserted, updated = self.database.batch_upsert_comments(
                    cursor, db_records
                )

                # Log success
                duration_ms = int((time.time() - start_time) * 1000)
                self.database.log_ingestion(
                    cursor=cursor,
                    run_id=run_id,
                    entity_type=entity_type,
                    records_fetched=records_fetched,
                    records_inserted=inserted,
                    records_updated=updated,
                    status="success",
                    duration_ms=duration_ms,
                )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Comments ingestion completed: fetched=%d, inserted=%d, updated=%d, duration=%dms",
                records_fetched,
                inserted,
                updated,
                duration_ms,
            )

            return IngestionResult(
                entity_type=entity_type,
                records_fetched=records_fetched,
                records_inserted=inserted,
                records_updated=updated,
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error("Comments ingestion failed: %s", error_msg)

            try:
                with self.database.transaction() as cursor:
                    self.database.log_ingestion(
                        cursor=cursor,
                        run_id=run_id,
                        entity_type=entity_type,
                        records_fetched=0,
                        records_inserted=0,
                        records_updated=0,
                        status="failed",
                        error_message=error_msg,
                        duration_ms=duration_ms,
                    )
            except Exception:
                logger.exception("Failed to log ingestion failure")

            return IngestionResult(
                entity_type=entity_type,
                records_fetched=0,
                records_inserted=0,
                records_updated=0,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )

    def run_full_ingestion(self) -> IngestionSummary:
        """Run complete ingestion for all entities.

        Ingests users, posts, and comments in sequence (users first
        due to foreign key constraints).

        Returns:
            IngestionSummary with results for all entities.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(tz=timezone.utc)
        logger.info("Starting full ingestion run, run_id=%s", run_id)

        results: list[IngestionResult] = []

        # Ingest in order: users -> posts -> comments (due to FK constraints)
        results.append(self.ingest_users(run_id))
        results.append(self.ingest_posts(run_id))
        results.append(self.ingest_comments(run_id))

        completed_at = datetime.now(tz=timezone.utc)
        total_records = sum(r.records_fetched for r in results)
        overall_success = all(r.success for r in results)

        summary = IngestionSummary(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            results=results,
            total_records=total_records,
            success=overall_success,
        )

        if overall_success:
            logger.info(
                "Full ingestion completed successfully: run_id=%s, total_records=%d",
                run_id,
                total_records,
            )
        else:
            failed = [r.entity_type for r in results if not r.success]
            logger.error(
                "Full ingestion completed with failures: run_id=%s, failed_entities=%s",
                run_id,
                failed,
            )

        return summary
