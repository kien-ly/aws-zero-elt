-- =============================================================================
-- Zero-ETL Demo Database Schema
-- Database: zero_etl_db
-- Engine: InnoDB (required for Zero-ETL)
-- Charset: utf8mb4
-- =============================================================================

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS zero_etl_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE zero_etl_db;

-- =============================================================================
-- Users Table
-- Source: JSONPlaceholder /users endpoint
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) DEFAULT NULL,
    website VARCHAR(255) DEFAULT NULL,
    -- Address fields (flattened from nested JSON)
    address_street VARCHAR(255) DEFAULT NULL,
    address_suite VARCHAR(100) DEFAULT NULL,
    address_city VARCHAR(100) DEFAULT NULL,
    address_zipcode VARCHAR(20) DEFAULT NULL,
    address_geo_lat DECIMAL(10, 7) DEFAULT NULL,
    address_geo_lng DECIMAL(10, 7) DEFAULT NULL,
    -- Company fields (flattened from nested JSON)
    company_name VARCHAR(255) DEFAULT NULL,
    company_catch_phrase TEXT DEFAULT NULL,
    company_bs TEXT DEFAULT NULL,
    -- Audit columns
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Constraints
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_email (email),
    UNIQUE KEY uk_users_username (username),
    -- Indexes
    INDEX idx_users_email (email),
    INDEX idx_users_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Posts Table
-- Source: JSONPlaceholder /posts endpoint
-- Note: Foreign key WITHOUT CASCADE for Zero-ETL compatibility
-- =============================================================================
CREATE TABLE IF NOT EXISTS posts (
    id INT NOT NULL,
    user_id INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    -- Audit columns
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Constraints
    PRIMARY KEY (id),
    -- Foreign key with RESTRICT (Zero-ETL does not support CASCADE)
    CONSTRAINT fk_posts_user_id
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    -- Indexes
    INDEX idx_posts_user_id (user_id),
    INDEX idx_posts_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Comments Table
-- Source: JSONPlaceholder /comments endpoint
-- Note: Foreign key WITHOUT CASCADE for Zero-ETL compatibility
-- =============================================================================
CREATE TABLE IF NOT EXISTS comments (
    id INT NOT NULL,
    post_id INT NOT NULL,
    name VARCHAR(500) NOT NULL,
    email VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    -- Audit columns
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Constraints
    PRIMARY KEY (id),
    -- Foreign key with RESTRICT (Zero-ETL does not support CASCADE)
    CONSTRAINT fk_comments_post_id
        FOREIGN KEY (post_id) REFERENCES posts(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    -- Indexes
    INDEX idx_comments_post_id (post_id),
    INDEX idx_comments_email (email),
    INDEX idx_comments_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Ingestion Log Table (for tracking Lambda runs)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ingestion_log (
    id BIGINT NOT NULL AUTO_INCREMENT,
    run_id VARCHAR(36) NOT NULL,
    entity_type ENUM('users', 'posts', 'comments') NOT NULL,
    records_fetched INT NOT NULL DEFAULT 0,
    records_inserted INT NOT NULL DEFAULT 0,
    records_updated INT NOT NULL DEFAULT 0,
    status ENUM('started', 'success', 'failed') NOT NULL,
    error_message TEXT DEFAULT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT NULL,
    duration_ms INT DEFAULT NULL,
    -- Constraints
    PRIMARY KEY (id),
    -- Indexes
    INDEX idx_ingestion_log_run_id (run_id),
    INDEX idx_ingestion_log_entity_type (entity_type),
    INDEX idx_ingestion_log_status (status),
    INDEX idx_ingestion_log_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Sample Queries for Redshift (after Zero-ETL sync)
-- These are example queries to run on Redshift side
-- =============================================================================
-- 
-- Count records per table:
-- SELECT 'users' as table_name, COUNT(*) as record_count FROM users
-- UNION ALL
-- SELECT 'posts', COUNT(*) FROM posts
-- UNION ALL
-- SELECT 'comments', COUNT(*) FROM comments;
--
-- Posts per user:
-- SELECT u.name, COUNT(p.id) as post_count
-- FROM users u
-- LEFT JOIN posts p ON u.id = p.user_id
-- GROUP BY u.id, u.name
-- ORDER BY post_count DESC;
--
-- Comments per post:
-- SELECT p.title, COUNT(c.id) as comment_count
-- FROM posts p
-- LEFT JOIN comments c ON p.id = c.post_id
-- GROUP BY p.id, p.title
-- ORDER BY comment_count DESC
-- LIMIT 10;
