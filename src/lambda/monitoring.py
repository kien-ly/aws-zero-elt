"""CloudWatch monitoring utilities for Zero-ETL integration.

This module provides functions to query CloudWatch metrics for
Lambda performance and Zero-ETL replication monitoring.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ZeroETLMonitoring:
    """CloudWatch metrics client for Zero-ETL monitoring.

    Provides methods to retrieve Lambda execution metrics and
    Zero-ETL replication lag statistics.

    Attributes:
        region: AWS region name.
    """

    def __init__(self, region: Optional[str] = None) -> None:
        """Initialize monitoring client.

        Args:
            region: AWS region name. Defaults to current region.
        """
        self.region = region
        self._client = boto3.client("cloudwatch", region_name=region)
        logger.info("ZeroETLMonitoring initialized for region=%s", region)

    def get_lambda_duration(
        self,
        function_name: str,
        period_minutes: int = 60,
    ) -> dict[str, Any]:
        """Get Lambda function duration metrics.

        Args:
            function_name: Name of the Lambda function.
            period_minutes: Time period to query (default: 60 minutes).

        Returns:
            Dictionary containing average, min, max duration in milliseconds.
        """
        end_time = datetime.now(tz=timezone.utc)
        start_time = end_time - timedelta(minutes=period_minutes)

        try:
            response = self._client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Duration",
                Dimensions=[
                    {
                        "Name": "FunctionName",
                        "Value": function_name,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minute periods
                Statistics=["Average", "Minimum", "Maximum", "Sum", "SampleCount"],
            )

            datapoints = response.get("Datapoints", [])
            if not datapoints:
                logger.warning(
                    "No duration metrics found for function=%s", function_name
                )
                return {
                    "function_name": function_name,
                    "period_minutes": period_minutes,
                    "datapoints": 0,
                    "average_ms": None,
                    "min_ms": None,
                    "max_ms": None,
                }

            # Sort by timestamp and get latest values
            sorted_points = sorted(
                datapoints, key=lambda x: x["Timestamp"], reverse=True
            )
            latest = sorted_points[0]

            result = {
                "function_name": function_name,
                "period_minutes": period_minutes,
                "datapoints": len(datapoints),
                "average_ms": round(latest.get("Average", 0), 2),
                "min_ms": round(latest.get("Minimum", 0), 2),
                "max_ms": round(latest.get("Maximum", 0), 2),
                "invocations": int(latest.get("SampleCount", 0)),
                "timestamp": latest["Timestamp"].isoformat(),
            }

            logger.info(
                "Lambda duration metrics: function=%s, avg=%sms, invocations=%d",
                function_name,
                result["average_ms"],
                result["invocations"],
            )
            return result

        except ClientError as e:
            logger.error("Failed to get Lambda duration metrics: %s", e)
            raise

    def get_lambda_errors(
        self,
        function_name: str,
        period_minutes: int = 60,
    ) -> dict[str, Any]:
        """Get Lambda function error count.

        Args:
            function_name: Name of the Lambda function.
            period_minutes: Time period to query (default: 60 minutes).

        Returns:
            Dictionary containing error count and rate.
        """
        end_time = datetime.now(tz=timezone.utc)
        start_time = end_time - timedelta(minutes=period_minutes)

        try:
            # Get errors
            error_response = self._client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Errors",
                Dimensions=[
                    {
                        "Name": "FunctionName",
                        "Value": function_name,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period_minutes * 60,
                Statistics=["Sum"],
            )

            # Get invocations
            invocation_response = self._client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[
                    {
                        "Name": "FunctionName",
                        "Value": function_name,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period_minutes * 60,
                Statistics=["Sum"],
            )

            error_datapoints = error_response.get("Datapoints", [])
            invocation_datapoints = invocation_response.get("Datapoints", [])

            total_errors = sum(dp.get("Sum", 0) for dp in error_datapoints)
            total_invocations = sum(dp.get("Sum", 0) for dp in invocation_datapoints)

            error_rate = 0.0
            if total_invocations > 0:
                error_rate = round((total_errors / total_invocations) * 100, 2)

            result = {
                "function_name": function_name,
                "period_minutes": period_minutes,
                "total_errors": int(total_errors),
                "total_invocations": int(total_invocations),
                "error_rate_percent": error_rate,
            }

            logger.info(
                "Lambda error metrics: function=%s, errors=%d, rate=%.2f%%",
                function_name,
                total_errors,
                error_rate,
            )
            return result

        except ClientError as e:
            logger.error("Failed to get Lambda error metrics: %s", e)
            raise

    def get_replication_lag(
        self,
        integration_identifier: str,
        period_minutes: int = 60,
    ) -> dict[str, Any]:
        """Get Zero-ETL replication lag metrics.

        Note: This uses the RDS integration metrics. The exact metric name
        may vary based on AWS documentation updates.

        Args:
            integration_identifier: Zero-ETL integration identifier.
            period_minutes: Time period to query (default: 60 minutes).

        Returns:
            Dictionary containing replication lag statistics.

        TODO: Verify exact metric namespace and name from AWS documentation.
              Current implementation uses expected metric pattern.
        """
        end_time = datetime.now(tz=timezone.utc)
        start_time = end_time - timedelta(minutes=period_minutes)

        try:
            # Zero-ETL replication metrics are under AWS/RDS namespace
            # Metric name: ZeroETLIntegrationLatency (approximate - verify with actual AWS docs)
            response = self._client.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName="ZeroETLIntegrationLatency",
                Dimensions=[
                    {
                        "Name": "IntegrationIdentifier",
                        "Value": integration_identifier,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minute periods
                Statistics=["Average", "Maximum"],
            )

            datapoints = response.get("Datapoints", [])
            if not datapoints:
                logger.warning(
                    "No replication lag metrics found for integration=%s",
                    integration_identifier,
                )
                return {
                    "integration_identifier": integration_identifier,
                    "period_minutes": period_minutes,
                    "datapoints": 0,
                    "average_lag_seconds": None,
                    "max_lag_seconds": None,
                    "status": "NO_DATA",
                }

            sorted_points = sorted(
                datapoints, key=lambda x: x["Timestamp"], reverse=True
            )
            latest = sorted_points[0]

            avg_lag = latest.get("Average", 0)
            max_lag = latest.get("Maximum", 0)

            # Determine status based on lag
            status = "HEALTHY"
            if avg_lag > 300:  # More than 5 minutes
                status = "WARNING"
            if avg_lag > 900:  # More than 15 minutes
                status = "CRITICAL"

            result = {
                "integration_identifier": integration_identifier,
                "period_minutes": period_minutes,
                "datapoints": len(datapoints),
                "average_lag_seconds": round(avg_lag, 2),
                "max_lag_seconds": round(max_lag, 2),
                "status": status,
                "timestamp": latest["Timestamp"].isoformat(),
            }

            logger.info(
                "Replication lag metrics: integration=%s, avg_lag=%.2fs, status=%s",
                integration_identifier,
                avg_lag,
                status,
            )
            return result

        except ClientError as e:
            # Handle case where metric doesn't exist yet
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(
                    "Replication lag metric not found for integration=%s",
                    integration_identifier,
                )
                return {
                    "integration_identifier": integration_identifier,
                    "period_minutes": period_minutes,
                    "datapoints": 0,
                    "average_lag_seconds": None,
                    "max_lag_seconds": None,
                    "status": "NOT_FOUND",
                }
            logger.error("Failed to get replication lag metrics: %s", e)
            raise

    def get_integration_health_dashboard(
        self,
        function_name: str,
        integration_identifier: Optional[str] = None,
        period_minutes: int = 60,
    ) -> dict[str, Any]:
        """Get comprehensive health dashboard for Zero-ETL integration.

        Combines Lambda and replication metrics into a single dashboard view.

        Args:
            function_name: Lambda function name.
            integration_identifier: Zero-ETL integration identifier (optional).
            period_minutes: Time period to query.

        Returns:
            Dictionary containing combined health metrics.
        """
        dashboard = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "period_minutes": period_minutes,
            "lambda": {
                "duration": self.get_lambda_duration(function_name, period_minutes),
                "errors": self.get_lambda_errors(function_name, period_minutes),
            },
            "overall_status": "HEALTHY",
        }

        # Add replication metrics if integration identifier provided
        if integration_identifier:
            dashboard["replication"] = self.get_replication_lag(
                integration_identifier, period_minutes
            )

        # Determine overall status
        error_rate = dashboard["lambda"]["errors"].get("error_rate_percent", 0)
        if error_rate > 5:
            dashboard["overall_status"] = "WARNING"
        if error_rate > 20:
            dashboard["overall_status"] = "CRITICAL"

        if integration_identifier:
            replication_status = dashboard.get("replication", {}).get(
                "status", "HEALTHY"
            )
            if replication_status in ["WARNING", "CRITICAL"]:
                dashboard["overall_status"] = replication_status

        logger.info(
            "Health dashboard generated: overall_status=%s",
            dashboard["overall_status"],
        )
        return dashboard
