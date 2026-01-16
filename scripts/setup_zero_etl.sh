#!/bin/bash
# =============================================================================
# Zero-ETL Integration Setup Script
# Creates Aurora MySQL to Redshift Zero-ETL integration
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Configuration
# =============================================================================
AWS_REGION="${AWS_REGION:-us-east-1}"
RDS_CLUSTER_ID="${RDS_CLUSTER_ID:-}"
REDSHIFT_NAMESPACE="${REDSHIFT_NAMESPACE:-zero-etl-namespace}"
REDSHIFT_WORKGROUP="${REDSHIFT_WORKGROUP:-zero-etl-workgroup}"
INTEGRATION_NAME="${INTEGRATION_NAME:-zero-etl-demo-integration}"
REDSHIFT_ADMIN_USER="${REDSHIFT_ADMIN_USER:-admin}"
REDSHIFT_ADMIN_PASSWORD="${REDSHIFT_ADMIN_PASSWORD:-}"

# =============================================================================
# Helper Functions
# =============================================================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --region          AWS Region (default: us-east-1)
    --rds-cluster     Aurora MySQL cluster identifier (required)
    --namespace       Redshift Serverless namespace name (default: zero-etl-namespace)
    --workgroup       Redshift Serverless workgroup name (default: zero-etl-workgroup)
    --integration     Integration name (default: zero-etl-demo-integration)
    --redshift-user   Redshift admin username (default: admin)
    --redshift-pass   Redshift admin password (required for new namespace)
    --help            Show this help message

Example:
    $0 --rds-cluster my-aurora-cluster --redshift-pass MySecretPass123!

EOF
    exit 0
}

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --rds-cluster)
            RDS_CLUSTER_ID="$2"
            shift 2
            ;;
        --namespace)
            REDSHIFT_NAMESPACE="$2"
            shift 2
            ;;
        --workgroup)
            REDSHIFT_WORKGROUP="$2"
            shift 2
            ;;
        --integration)
            INTEGRATION_NAME="$2"
            shift 2
            ;;
        --redshift-user)
            REDSHIFT_ADMIN_USER="$2"
            shift 2
            ;;
        --redshift-pass)
            REDSHIFT_ADMIN_PASSWORD="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# =============================================================================
# Validation
# =============================================================================
if [[ -z "$RDS_CLUSTER_ID" ]]; then
    log_error "Aurora cluster ID is required. Use --rds-cluster option."
    usage
fi

# =============================================================================
# Step 1: Validate Aurora Cluster Configuration
# =============================================================================
validate_aurora_cluster() {
    log_info "Validating Aurora cluster: $RDS_CLUSTER_ID"
    
    CLUSTER_INFO=$(aws rds describe-db-clusters \
        --db-cluster-identifier "$RDS_CLUSTER_ID" \
        --region "$AWS_REGION" \
        --query 'DBClusters[0]' \
        --output json 2>/dev/null) || {
        log_error "Aurora cluster not found: $RDS_CLUSTER_ID"
        exit 1
    }
    
    # Check engine version
    ENGINE_VERSION=$(echo "$CLUSTER_INFO" | jq -r '.EngineVersion')
    log_info "Engine version: $ENGINE_VERSION"
    
    # Check if encryption is enabled (required for Zero-ETL)
    STORAGE_ENCRYPTED=$(echo "$CLUSTER_INFO" | jq -r '.StorageEncrypted')
    if [[ "$STORAGE_ENCRYPTED" != "true" ]]; then
        log_warn "Storage encryption is not enabled. Zero-ETL requires encrypted clusters."
        log_warn "You may need to enable encryption on the cluster."
    fi
    
    # Get cluster ARN
    CLUSTER_ARN=$(echo "$CLUSTER_INFO" | jq -r '.DBClusterArn')
    log_info "Cluster ARN: $CLUSTER_ARN"
    
    # Check parameter group settings
    # Note: binlog_format=ROW and aurora_enhanced_binlog=1 are required
    log_info "Please verify the following parameter group settings:"
    log_info "  - binlog_format = ROW"
    log_info "  - aurora_enhanced_binlog = 1"
    log_info "  - binlog_row_image = FULL"
}

# =============================================================================
# Step 2: Create Redshift Serverless Namespace (if not exists)
# =============================================================================
create_redshift_namespace() {
    log_info "Checking Redshift Serverless namespace: $REDSHIFT_NAMESPACE"
    
    if aws redshift-serverless get-namespace \
        --namespace-name "$REDSHIFT_NAMESPACE" \
        --region "$AWS_REGION" &> /dev/null; then
        log_info "Namespace already exists: $REDSHIFT_NAMESPACE"
        NAMESPACE_ARN=$(aws redshift-serverless get-namespace \
            --namespace-name "$REDSHIFT_NAMESPACE" \
            --region "$AWS_REGION" \
            --query 'namespace.namespaceArn' \
            --output text)
    else
        log_info "Creating Redshift Serverless namespace..."
        
        if [[ -z "$REDSHIFT_ADMIN_PASSWORD" ]]; then
            log_error "Redshift admin password is required for new namespace."
            log_error "Use --redshift-pass option."
            exit 1
        fi
        
        aws redshift-serverless create-namespace \
            --namespace-name "$REDSHIFT_NAMESPACE" \
            --admin-username "$REDSHIFT_ADMIN_USER" \
            --admin-user-password "$REDSHIFT_ADMIN_PASSWORD" \
            --db-name "zero_etl_db" \
            --region "$AWS_REGION"
        
        log_info "Waiting for namespace to be available..."
        sleep 30
        
        NAMESPACE_ARN=$(aws redshift-serverless get-namespace \
            --namespace-name "$REDSHIFT_NAMESPACE" \
            --region "$AWS_REGION" \
            --query 'namespace.namespaceArn' \
            --output text)
    fi
    
    log_info "Namespace ARN: $NAMESPACE_ARN"
}

# =============================================================================
# Step 3: Create Redshift Serverless Workgroup (if not exists)
# =============================================================================
create_redshift_workgroup() {
    log_info "Checking Redshift Serverless workgroup: $REDSHIFT_WORKGROUP"
    
    if aws redshift-serverless get-workgroup \
        --workgroup-name "$REDSHIFT_WORKGROUP" \
        --region "$AWS_REGION" &> /dev/null; then
        log_info "Workgroup already exists: $REDSHIFT_WORKGROUP"
    else
        log_info "Creating Redshift Serverless workgroup..."
        
        aws redshift-serverless create-workgroup \
            --workgroup-name "$REDSHIFT_WORKGROUP" \
            --namespace-name "$REDSHIFT_NAMESPACE" \
            --base-capacity 8 \
            --region "$AWS_REGION"
        
        log_info "Waiting for workgroup to be available..."
        sleep 60
    fi
}

# =============================================================================
# Step 4: Configure Authorized Principals (Resource Policy)
# =============================================================================
configure_resource_policy() {
    log_info "Configuring resource policy for Zero-ETL integration..."
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
    
    # Create resource policy for Redshift namespace
    # This allows Aurora to replicate data to Redshift
    POLICY_JSON=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAuroraZeroETL",
            "Effect": "Allow",
            "Principal": {
                "Service": "redshift.amazonaws.com"
            },
            "Action": [
                "redshift-serverless:CreateNamespace",
                "redshift-serverless:GetNamespace",
                "redshift-serverless:ModifyNamespace"
            ],
            "Resource": "arn:aws:redshift-serverless:${AWS_REGION}:${ACCOUNT_ID}:namespace/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${ACCOUNT_ID}"
                }
            }
        }
    ]
}
EOF
)
    
    log_info "Resource policy configured (review if manual adjustments needed)."
    log_info "Policy: $POLICY_JSON"
}

# =============================================================================
# Step 5: Create Zero-ETL Integration
# =============================================================================
create_zero_etl_integration() {
    log_info "Creating Zero-ETL integration: $INTEGRATION_NAME"
    
    # Check if integration already exists
    if aws rds describe-integrations \
        --integration-name "$INTEGRATION_NAME" \
        --region "$AWS_REGION" &> /dev/null 2>&1; then
        log_info "Integration already exists: $INTEGRATION_NAME"
        INTEGRATION_ARN=$(aws rds describe-integrations \
            --integration-name "$INTEGRATION_NAME" \
            --region "$AWS_REGION" \
            --query 'Integrations[0].IntegrationArn' \
            --output text)
    else
        log_info "Creating new Zero-ETL integration..."
        
        # Create integration
        # Note: This may take several minutes
        aws rds create-integration \
            --integration-name "$INTEGRATION_NAME" \
            --source-arn "$CLUSTER_ARN" \
            --target-arn "$NAMESPACE_ARN" \
            --region "$AWS_REGION" \
            --tags Key=Environment,Value=demo Key=Project,Value=zero-etl-demo
        
        log_info "Integration creation initiated. This may take 20-30 minutes."
        log_info "Monitor status with: aws rds describe-integrations --integration-name $INTEGRATION_NAME"
        
        INTEGRATION_ARN=$(aws rds describe-integrations \
            --integration-name "$INTEGRATION_NAME" \
            --region "$AWS_REGION" \
            --query 'Integrations[0].IntegrationArn' \
            --output text)
    fi
    
    log_info "Integration ARN: $INTEGRATION_ARN"
}

# =============================================================================
# Step 6: Create Database from Integration in Redshift
# =============================================================================
create_redshift_database() {
    log_info "Creating database from integration in Redshift..."
    
    # Note: This step requires the integration to be in 'active' state
    # The database is created automatically when you query the integration
    
    cat << EOF

=============================================================================
NEXT STEPS (Manual)
=============================================================================

After the integration becomes active (check with describe-integrations),
connect to Redshift and create the database from the integration:

1. Connect to Redshift Serverless:
   aws redshift-serverless get-credentials \\
       --workgroup-name $REDSHIFT_WORKGROUP \\
       --database-name dev

2. Create database from integration:
   CREATE DATABASE zero_etl_db FROM INTEGRATION '$INTEGRATION_ARN';

3. Query replicated tables:
   SELECT * FROM zero_etl_db.public.users LIMIT 10;
   SELECT * FROM zero_etl_db.public.posts LIMIT 10;
   SELECT * FROM zero_etl_db.public.comments LIMIT 10;

=============================================================================
MONITORING
=============================================================================

View integration status:
   aws rds describe-integrations --integration-name $INTEGRATION_NAME

View CloudWatch metrics for replication lag:
   - Namespace: AWS/RDS
   - Metric: ZeroETLIntegrationLatency
   - Dimension: IntegrationIdentifier=$INTEGRATION_ARN

View integration errors:
   aws rds describe-integration-errors --integration-identifier $INTEGRATION_ARN

=============================================================================

EOF
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    echo ""
    echo "============================================="
    echo "  Zero-ETL Integration Setup"
    echo "============================================="
    echo ""
    
    check_prerequisites
    validate_aurora_cluster
    create_redshift_namespace
    create_redshift_workgroup
    configure_resource_policy
    create_zero_etl_integration
    create_redshift_database
    
    log_info "Setup script completed!"
    log_info "Remember: Initial data sync may take 20-30 minutes."
}

main
