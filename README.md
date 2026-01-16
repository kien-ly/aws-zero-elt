# AWS Zero-ETL Demo: Aurora MySQL → Redshift

A demonstration of AWS Zero-ETL integration that automatically replicates data from Aurora MySQL to Amazon Redshift for near real-time analytics.

## Architecture

```
┌─────────────────────┐
│  JSONPlaceholder    │  (Public REST API)
│  /users /posts      │
│  /comments          │
└─────────┬───────────┘
          │ HTTPS
          ▼
┌─────────────────────┐    EventBridge
│   AWS Lambda        │◄── Scheduled Rule
│   (Python 3.12)     │    (every 5 min)
│   Batch Ingest      │
└─────────┬───────────┘
          │ MySQL (VPC)
          ▼
┌─────────────────────┐
│  Amazon Aurora      │
│  MySQL 3.04+        │
│  (Zero-ETL source)  │
└─────────┬───────────┘
          │ Zero-ETL (CDC)
          ▼
┌─────────────────────┐
│  Amazon Redshift    │
│  Serverless         │
│  (Analytics)        │
└─────────────────────┘
```

## Features

- **Dependency Injection**: Lambda uses DI container pattern for testability
- **Batch Ingestion**: Efficient batch upsert operations with transaction rollback
- **Zero-ETL Integration**: Automatic CDC replication from Aurora to Redshift
- **Monitoring**: CloudWatch metrics for Lambda performance and replication lag
- **IaC**: Complete AWS SAM template for reproducible deployments

## Prerequisites

- AWS CLI v2 configured with appropriate credentials
- AWS SAM CLI (`pip install aws-sam-cli`)
- Python 3.12+
- Docker (for SAM local testing)

## Project Structure

```
zero-etl/
├── template.yaml              # SAM template (VPC, Aurora, Lambda)
├── src/
│   └── lambda/
│       ├── handler.py         # Lambda entry point
│       ├── container.py       # DI container
│       ├── models.py          # Dataclasses
│       ├── api_client.py      # JSONPlaceholder client
│       ├── database.py        # MySQL connection manager
│       ├── processor.py       # Data transformer
│       ├── service.py         # Orchestration service
│       ├── monitoring.py      # CloudWatch metrics
│       └── requirements.txt
├── db/
│   └── schema.sql             # Database DDL
├── scripts/
│   └── setup_zero_etl.sh      # Zero-ETL integration setup
└── README.md
```

## Deployment

### 1. Build and Deploy SAM Stack

```bash
# Build the application
sam build

# Deploy with guided prompts
sam deploy --guided
```

You'll be prompted for:
- Stack Name: `zero-etl-demo`
- AWS Region: Your preferred region
- DBPassword: Strong password (min 8 chars)
- Confirm changeset deployment

### 2. Initialize Database Schema

After deployment, connect to Aurora and run the schema:

```bash
# Get Aurora endpoint from stack outputs
AURORA_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name zero-etl-demo \
    --query 'Stacks[0].Outputs[?OutputKey==`AuroraClusterEndpoint`].OutputValue' \
    --output text)

# Connect via bastion host or Cloud9 and run schema
mysql -h $AURORA_ENDPOINT -u admin -p < db/schema.sql
```

### 3. Setup Zero-ETL Integration

```bash
# Make script executable
chmod +x scripts/setup_zero_etl.sh

# Run setup (replace with your cluster ID)
./scripts/setup_zero_etl.sh \
    --rds-cluster zero-etl-demo-cluster \
    --redshift-pass YourSecurePassword123!
```

### 4. Verify Lambda Execution

```bash
# Manually invoke Lambda
sam remote invoke IngestFunction --stack-name zero-etl-demo

# Or wait for scheduled execution (every 5 minutes)
```

## Verification

### Check Aurora Data

```sql
-- Connect to Aurora MySQL
USE zero_etl_db;

SELECT COUNT(*) FROM users;      -- Should be 10
SELECT COUNT(*) FROM posts;      -- Should be 100
SELECT COUNT(*) FROM comments;   -- Should be 500

-- View recent ingestion logs
SELECT * FROM ingestion_log ORDER BY started_at DESC LIMIT 10;
```

### Check Redshift Data (after Zero-ETL sync)

```sql
-- Connect to Redshift
-- Note: Initial sync takes 20-30 minutes

SELECT COUNT(*) FROM zero_etl_db.public.users;
SELECT COUNT(*) FROM zero_etl_db.public.posts;
SELECT COUNT(*) FROM zero_etl_db.public.comments;

-- Analytics query example
SELECT u.name, COUNT(p.id) as post_count
FROM zero_etl_db.public.users u
LEFT JOIN zero_etl_db.public.posts p ON u.id = p.user_id
GROUP BY u.id, u.name
ORDER BY post_count DESC;
```

## Monitoring

### Lambda Logs

```bash
# View recent logs
sam logs -n IngestFunction --stack-name zero-etl-demo --tail

# Or via AWS CLI
aws logs tail /aws/lambda/zero-etl-demo-ingest --follow
```

### CloudWatch Metrics

| Metric | Namespace | Description |
|--------|-----------|-------------|
| Duration | AWS/Lambda | Lambda execution time |
| Errors | AWS/Lambda | Lambda error count |
| Invocations | AWS/Lambda | Total invocations |
| ZeroETLIntegrationLatency | AWS/RDS | Replication lag |

### CloudWatch Dashboard Query

```
SELECT AVG(Duration) 
FROM SCHEMA("AWS/Lambda", FunctionName) 
WHERE FunctionName = 'zero-etl-demo-ingest'
```

## Local Development

### Run Lambda Locally

```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=zero_etl_db
export DB_USER=admin
export DB_PASSWORD=your_password

# Install dependencies
cd src/lambda
pip install -r requirements.txt

# Run handler directly
python handler.py
```

### Run with SAM Local

```bash
# Start local API (requires Docker)
sam local invoke IngestFunction --event events/scheduled.json
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DB_HOST | Aurora endpoint | - |
| DB_PORT | MySQL port | 3306 |
| DB_NAME | Database name | zero_etl_db |
| DB_USER | Database user | admin |
| DB_PASSWORD | Database password | - |
| API_ENDPOINT | JSONPlaceholder URL | https://jsonplaceholder.typicode.com |
| LOG_LEVEL | Logging level | INFO |

### SAM Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Environment | Deployment environment | dev |
| DBPassword | Aurora admin password | - |
| VpcCIDR | VPC CIDR block | 10.0.0.0/16 |

## Cleanup

```bash
# Delete SAM stack
sam delete --stack-name zero-etl-demo

# Delete Zero-ETL integration (if created)
aws rds delete-integration --integration-identifier <integration-arn>

# Delete Redshift resources
aws redshift-serverless delete-workgroup --workgroup-name zero-etl-workgroup
aws redshift-serverless delete-namespace --namespace-name zero-etl-namespace
```

## Limitations

- Foreign keys with `ON DELETE/UPDATE CASCADE` are not supported by Zero-ETL
- Initial sync can take 20-30 minutes
- Some MySQL data types may require mapping adjustments
- XA transactions may cause sync delays

## References

- [Aurora Zero-ETL Integrations](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.html)
- [JSONPlaceholder API](https://jsonplaceholder.typicode.com/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
