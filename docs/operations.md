# Operational Guide: AWS Zero-ETL Demo

This guide provides detailed instructions on how to set up, operate, and maintain the Zero-ETL demo project.

## 1. Environment Setup

### Prerequisites

Ensure you have the following tools installed:

1.  **Python 3.12+**: [Download Python](https://www.python.org/downloads/)
2.  **AWS CLI v2**: [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
    *   Run `aws configure` to set up your credentials.
3.  **AWS SAM CLI**: [Install Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
4.  **Docker**: Required for running Lambda locally via SAM.
5.  **MySQL Client**: For connecting to Aurora (e.g., MySQL Workbench, DBeaver, or command line `mysql`).

### Local Project Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd zero-etl
    ```

2.  **Create a virtual environment:**
    ```bash
    # Using venv
    python3.12 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r src/lambda/requirements.txt
    pip install -r requirements-dev.txt # If you have dev dependencies like ruff
    ```

4.  **Environment Variables:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    *   Edit `.env` if you are running scripts locally against a deployed database (via SSH tunnel) or a local MySQL instance.

---

## 2. Deployment (Infrastructure as Code)

We use AWS SAM to deploy the entire stack.

### Step 1: Build

Compile the Lambda function and prepare the deployment package.

```bash
sam build
```

### Step 2: Deploy

Deploy the CloudFormation stack.

```bash
sam deploy --guided
```

**Configuration Prompts:**
*   **Stack Name**: `zero-etl-demo`
*   **AWS Region**: `us-east-1` (or your preferred region)
*   **Parameter DBPassword**: Enter a strong password (min 8 chars). **SAVE THIS PASSWORD.**
*   **Confirm changes before deploy**: `Y`
*   **Allow SAM CLI IAM role creation**: `Y`
*   **Save arguments to configuration file**: `Y`

### Step 3: Post-Deployment Configuration (CRITICAL)

After the stack is created successfully:

1.  **Get Outputs:**
    Note the `AuroraClusterEndpoint` from the SAM deployment output.

2.  **Reboot Writer Instance:**
    The parameter group changes (`binlog_format=ROW`) require a reboot.
    ```bash
    # Find your instance identifier (usually zero-etl-demo-instance-1)
    aws rds describe-db-instances --query "DBInstances[*].DBInstanceIdentifier"

    # Reboot
    aws rds reboot-db-instance --db-instance-identifier <your-instance-id>
    ```

3.  **Initialize Database Schema:**
    You need to connect to the private Aurora instance.
    *   **Option A: VPN / Direct Connect** (Enterprise)
    *   **Option B: Bastion Host** (Recommended for this demo) - *Not included in template, create an EC2 in the public subnet if needed.*
    *   **Option C: Cloud9** (Easiest) - Create a Cloud9 environment in the same VPC.

    Once connected:
    ```bash
    mysql -h <AuroraClusterEndpoint> -u admin -p < db/schema.sql
    ```

4.  **Setup Zero-ETL Integration:**
    Run the helper script:
    ```bash
    chmod +x scripts/setup_zero_etl.sh
    ./scripts/setup_zero_etl.sh \
        --rds-cluster <AuroraClusterIdentifier> \
        --redshift-pass <NewRedshiftPassword>
    ```

---

## 3. Local Development & Testing

### Linting

Check code quality before deploying.

```bash
pip install ruff
ruff check src/lambda
```

### Running Lambda Locally

You can simulate the Lambda execution locally using Docker.

1.  Create a `env.json` file for SAM (based on your `.env`):
    ```json
    {
      "IngestFunction": {
        "DB_HOST": "host.docker.internal",
        "DB_USER": "root",
        "DB_PASSWORD": "localpassword",
        "DB_NAME": "zero_etl_db",
        "API_ENDPOINT": "https://jsonplaceholder.typicode.com"
      }
    }
    ```
    *Note: Use `host.docker.internal` to access a local MySQL running on your machine.*

2.  Invoke the function:
    ```bash
    sam local invoke IngestFunction --env-vars env.json
    ```

---

## 4. Monitoring & Operations

### Check Lambda Logs

View real-time logs from CloudWatch.

```bash
sam logs -n IngestFunction --stack-name zero-etl-demo --tail
```

### Monitor Zero-ETL Lag

1.  Go to **CloudWatch Console**.
2.  Navigate to **Metrics** > **All metrics** > **RDS**.
3.  Search for `ZeroETLIntegrationLatency`.
4.  This metric shows the lag in seconds (should be < 15s typically).

### Verify Data in Redshift

1.  Go to **Redshift Query Editor v2**.
2.  Connect to your Serverless Workgroup.
3.  Create the database from integration (one-time setup):
    ```sql
    CREATE DATABASE zero_etl_db FROM INTEGRATION 'arn:aws:rds...';
    ```
4.  Query data:
    ```sql
    SELECT * FROM zero_etl_db.zero_etl_db.users LIMIT 10;
    ```

---

## 5. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **Lambda Timeout** | NAT Gateway missing or API slow | Check VPC routes. Increase Lambda timeout in `template.yaml`. |
| **DB Connection Fail** | Security Group / VPC | Ensure Lambda SG allows outbound 3306 to Aurora SG. |
| **Zero-ETL Broken** | Parameter Group not applied | **Reboot the Aurora Writer instance.** |
| **Zero-ETL Broken** | FK Cascade used | Check `db/schema.sql`. Use `ON DELETE RESTRICT`. |

---

## 6. Cleanup

To avoid ongoing costs (especially Aurora and NAT Gateway), delete the stack when done.

```bash
# 1. Delete Zero-ETL Integration (via script or console)
aws rds delete-integration --integration-identifier <integration-arn>

# 2. Delete Redshift Namespace (if created manually)

# 3. Delete SAM Stack
sam delete
```
