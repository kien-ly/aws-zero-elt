# AWS Zero-ETL Architecture Documentation

## Overview

This document describes the architecture of the AWS Zero-ETL demo that replicates data from Aurora MySQL to Amazon Redshift in near real-time.

## Architecture Diagram

```mermaid
flowchart TB
    API[JSONPlaceholder API] -->|HTTPS| Lambda
    EB[EventBridge] -->|Trigger 5min| Lambda
    Lambda[Lambda Function] -->|SQL| Aurora[(Aurora MySQL)]
    Aurora -.->|Zero-ETL CDC| Redshift[(Redshift)]
```

## Components

### 1. Data Source: JSONPlaceholder API

| Endpoint | Description | Record Count |
|----------|-------------|--------------|
| `/users` | User profiles | 10 |
| `/posts` | Blog posts | 100 |
| `/comments` | Comments | 500 |

---

### 2. Ingestion Layer: AWS Lambda

**Runtime:** Python 3.12  
**Schedule:** Every 5 minutes

#### Code Architecture (DI)

```mermaid
flowchart TB
    Handler --> Container[ServiceContainer]
    Container --> APIClient
    Container --> Database
    Container --> Processor
    APIClient --> Service[ZeroETLService]
    Database --> Service
    Processor --> Service
```

#### Ingestion Flow

```mermaid
flowchart TD
    A[1. Fetch from API] --> B[2. Transform JSON]
    B --> C[3. Batch Upsert to MySQL]
    C --> D[4. Log Result]
```

---

### 3. Database: Aurora MySQL

**Engine:** Aurora MySQL 8.0 (3.04+)  
**Storage:** Encrypted

#### Zero-ETL Configuration

| Parameter | Value |
|-----------|-------|
| `binlog_format` | `ROW` |
| `aurora_enhanced_binlog` | `1` |
| `binlog_row_image` | `FULL` |

#### Schema

```mermaid
erDiagram
    users ||--o{ posts : has
    posts ||--o{ comments : has
    
    users {
        int id PK
        varchar name
        varchar email
    }
    
    posts {
        int id PK
        int user_id FK
        varchar title
        text body
    }
    
    comments {
        int id PK
        int post_id FK
        varchar email
        text body
    }
```

---

### 4. Zero-ETL Integration

**Type:** Aurora MySQL → Redshift  
**Latency:** Seconds to minutes

#### How It Works

```mermaid
flowchart LR
    Aurora[(Aurora)] -->|Binary Log| CDC[CDC Stream]
    CDC -->|Auto| Redshift[(Redshift)]
```

| Phase | Duration |
|-------|----------|
| Integration Creation | 1-2 min |
| Initial Seed | 20-30 min |
| CDC Active | Ongoing |

---

### 5. Analytics: Redshift

```sql
-- Posts per user
SELECT u.name, COUNT(p.id) as posts
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id, u.name;
```

---

### 6. Monitoring

| Metric | Namespace |
|--------|-----------|
| Duration | AWS/Lambda |
| Errors | AWS/Lambda |
| ReplicationLag | AWS/RDS |

---

## Security

```mermaid
flowchart TB
    subgraph VPC
        subgraph Public
            NAT[NAT Gateway]
        end
        subgraph Private
            Lambda --> Aurora[(Aurora)]
        end
        Lambda --> NAT
    end
    NAT --> Internet
```

| Layer | Protection |
|-------|------------|
| Database | Encryption at rest |
| Network | TLS in transit |
| IAM | Least privilege |

---

## Cost Estimation

| Service | Est. Cost/Month |
|---------|-----------------|
| Aurora MySQL | ~$200 |
| Lambda | ~$5 |
| NAT Gateway | ~$35 |
| Redshift | ~$50 |
| **Total** | **~$290** |

---

## Data Flow

```mermaid
sequenceDiagram
    EB->>Lambda: Trigger
    Lambda->>API: GET data
    API-->>Lambda: JSON
    Lambda->>Aurora: INSERT
    Aurora-->>Redshift: CDC Replicate
```

---

## References

- [Aurora Zero-ETL](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.html)
- [Redshift Serverless](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-whatis.html)
