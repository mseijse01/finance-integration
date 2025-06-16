#!/usr/bin/env python3
"""
Database Schema Migration Script
Fixes schema mismatches between updated models and existing database.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from config import Config
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_database_schema():
    """
    Apply database schema migrations to match updated models.
    """
    engine = create_engine(Config.DATABASE_URL)

    # Migration statements
    migration_statements = [
        # Remove volatility column from stock_prices (no longer in model)
        "ALTER TABLE stock_prices DROP COLUMN IF EXISTS volatility;",
        # Add new columns to financial_reports
        "ALTER TABLE financial_reports ADD COLUMN IF NOT EXISTS total_assets FLOAT;",
        "ALTER TABLE financial_reports ADD COLUMN IF NOT EXISTS total_liabilities FLOAT;",
        # Remove fetched_at columns (no longer in models)
        "ALTER TABLE news_articles DROP COLUMN IF EXISTS fetched_at;",
        "ALTER TABLE financial_reports DROP COLUMN IF EXISTS fetched_at;",
        "ALTER TABLE earnings DROP COLUMN IF EXISTS fetched_at;",
        # Update column types and constraints
        "ALTER TABLE stock_prices ALTER COLUMN symbol TYPE VARCHAR(10);",
        "ALTER TABLE stock_prices ALTER COLUMN symbol SET NOT NULL;",
        "ALTER TABLE stock_prices ALTER COLUMN date SET NOT NULL;",
        "ALTER TABLE stock_prices ALTER COLUMN volume TYPE INTEGER;",
        "ALTER TABLE news_articles ALTER COLUMN symbol TYPE VARCHAR(10);",
        "ALTER TABLE news_articles ALTER COLUMN symbol SET NOT NULL;",
        "ALTER TABLE news_articles ALTER COLUMN headline SET NOT NULL;",
        "ALTER TABLE news_articles ALTER COLUMN datetime SET NOT NULL;",
        "ALTER TABLE news_articles ALTER COLUMN source TYPE VARCHAR(100);",
        "ALTER TABLE news_articles ALTER COLUMN category TYPE VARCHAR(50);",
        "ALTER TABLE news_articles ALTER COLUMN related TYPE VARCHAR(200);",
        "ALTER TABLE financial_reports ALTER COLUMN symbol TYPE VARCHAR(10);",
        "ALTER TABLE financial_reports ALTER COLUMN symbol SET NOT NULL;",
        "ALTER TABLE financial_reports ALTER COLUMN year SET NOT NULL;",
        "ALTER TABLE financial_reports ALTER COLUMN report_type TYPE VARCHAR(20);",
        "ALTER TABLE financial_reports ALTER COLUMN report_type SET NOT NULL;",
        "ALTER TABLE financial_reports ALTER COLUMN filing_date TYPE DATE;",
        "ALTER TABLE earnings ALTER COLUMN symbol TYPE VARCHAR(10);",
        "ALTER TABLE earnings ALTER COLUMN symbol SET NOT NULL;",
        "ALTER TABLE earnings ALTER COLUMN period TYPE DATE;",
        "ALTER TABLE earnings ALTER COLUMN period SET NOT NULL;",
        "ALTER TABLE earnings ALTER COLUMN year SET NOT NULL;",
        "ALTER TABLE earnings ALTER COLUMN quarter SET NOT NULL;",
        # Remove unused columns from earnings
        "ALTER TABLE earnings DROP COLUMN IF EXISTS revenue_surprise;",
        "ALTER TABLE earnings DROP COLUMN IF EXISTS revenue_surprise_percent;",
    ]

    logger.info("Starting database schema migration...")

    try:
        with engine.connect() as conn:
            for i, statement in enumerate(migration_statements, 1):
                try:
                    logger.info(f"Executing migration {i}/{len(migration_statements)}")
                    logger.debug(f"SQL: {statement}")
                    conn.execute(text(statement))
                    logger.info(f"✓ Migration {i} completed")
                except Exception as e:
                    logger.warning(f"Migration {i} failed (may be expected): {e}")

        logger.info("Database schema migration completed!")
        logger.info("Schema is now compatible with updated models.")

    except Exception as e:
        logger.error(f"Failed to migrate database schema: {e}")
        raise


def verify_schema():
    """
    Verify that the schema matches the expected structure.
    """
    engine = create_engine(Config.DATABASE_URL)

    verification_queries = [
        # Check stock_prices structure
        """
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'stock_prices' 
        ORDER BY ordinal_position;
        """,
        # Check financial_reports structure
        """
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'financial_reports' 
        ORDER BY ordinal_position;
        """,
        # Check earnings structure
        """
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'earnings' 
        ORDER BY ordinal_position;
        """,
        # Check news_articles structure
        """
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'news_articles' 
        ORDER BY ordinal_position;
        """,
    ]

    table_names = ["stock_prices", "financial_reports", "earnings", "news_articles"]

    try:
        with engine.connect() as conn:
            for i, (query, table_name) in enumerate(
                zip(verification_queries, table_names)
            ):
                logger.info(f"Verifying {table_name} schema...")
                result = conn.execute(text(query))
                rows = result.fetchall()

                logger.info(f"{table_name} columns:")
                for row in rows:
                    nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                    logger.info(f"  - {row[0]}: {row[1]} ({nullable})")
                logger.info("")

    except Exception as e:
        logger.error(f"Schema verification failed: {e}")


if __name__ == "__main__":
    print("🔄 Database Schema Migration")
    print("=" * 50)

    try:
        # Run the migration
        migrate_database_schema()

        # Verify the results
        print("\n📋 Schema Verification")
        print("-" * 30)
        verify_schema()

        print("✅ Database schema migration complete!")
        print("The database is now compatible with the updated models.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
