"""AWS Lambda handler for Zero-ETL data ingestion.

This module provides the Lambda entry point that initializes the DI container
and executes the data ingestion pipeline from JSONPlaceholder API to Aurora MySQL.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

# Configure logging before other imports
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Reduce noise from third-party libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("mysql.connector").setLevel(logging.WARNING)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for data ingestion.

    Initializes DI container, runs full ingestion pipeline, and returns
    a summary of the operation.

    Args:
        event: Lambda event data (from EventBridge scheduled rule).
        context: Lambda context object.

    Returns:
        Dictionary containing:
            - statusCode: HTTP status code (200 for success, 500 for failure)
            - body: JSON string with ingestion summary
    """
    from container import create_container

    logger.info(
        "Lambda invoked: request_id=%s, event_source=%s",
        getattr(context, "aws_request_id", "local"),
        event.get("source", "unknown"),
    )

    container = None
    try:
        # Initialize DI container
        container = create_container()

        # Get the Zero-ETL service from container
        zero_etl_service = container.resolve("zero_etl_service")

        # Run full ingestion
        summary = zero_etl_service.run_full_ingestion()

        # Build response
        response_body = {
            "run_id": summary.run_id,
            "success": summary.success,
            "started_at": summary.started_at.isoformat(),
            "completed_at": summary.completed_at.isoformat(),
            "total_records": summary.total_records,
            "results": [
                {
                    "entity_type": r.entity_type,
                    "records_fetched": r.records_fetched,
                    "records_inserted": r.records_inserted,
                    "records_updated": r.records_updated,
                    "duration_ms": r.duration_ms,
                    "success": r.success,
                    "error_message": r.error_message,
                }
                for r in summary.results
            ],
        }

        status_code = (
            200 if summary.success else 207
        )  # 207 Multi-Status for partial failure

        logger.info(
            "Lambda completed: run_id=%s, success=%s, total_records=%d",
            summary.run_id,
            summary.success,
            summary.total_records,
        )

        return {
            "statusCode": status_code,
            "body": json.dumps(response_body),
            "headers": {
                "Content-Type": "application/json",
            },
        }

    except Exception as e:
        logger.exception("Lambda execution failed: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
            ),
            "headers": {
                "Content-Type": "application/json",
            },
        }

    finally:
        # Ensure resources are cleaned up
        if container is not None:
            try:
                container.dispose()
                logger.debug("Container disposed successfully")
            except Exception:
                logger.exception("Error disposing container")


# For local testing
if __name__ == "__main__":
    # Mock context for local execution
    class MockContext:
        aws_request_id = "local-test"
        function_name = "zero-etl-ingest"
        memory_limit_in_mb = 256
        invoked_function_arn = "arn:aws:lambda:local:123456789:function:zero-etl-ingest"

    # Set environment variables for local testing
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "3306")
    os.environ.setdefault("DB_NAME", "zero_etl_db")
    os.environ.setdefault("DB_USER", "admin")
    os.environ.setdefault("DB_PASSWORD", "your_password_here")
    os.environ.setdefault("API_ENDPOINT", "https://jsonplaceholder.typicode.com")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")

    # Execute handler
    result = lambda_handler(
        event={"source": "local-test"},
        context=MockContext(),
    )
    print(json.dumps(json.loads(result["body"]), indent=2))
