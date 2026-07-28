-- Init script for PostgreSQL
-- Creates the database schema and initial admin user

-- The database is already created by POSTGRES_DB env var
-- This script adds the initial admin user

-- Note: Tables are created by SQLAlchemy on app startup via alembic or create_all
-- This is a placeholder for any raw SQL initialization needed

-- Create extension for UUID if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
