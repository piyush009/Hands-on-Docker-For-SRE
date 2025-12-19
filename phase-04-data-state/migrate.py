#!/usr/bin/env python3
"""
Phase 4 migration script.

Simulates a schema evolution by adding a new column to the users table.
Run via:
    docker compose run --rm migrator
"""

import os
import psycopg2

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "appdb"),
    "user": os.getenv("DB_USER", "appuser"),
    "password": os.getenv("DB_PASSWORD", "apppass"),
}


def main():
    print("Running Phase 4 migration...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"Failed to connect to DB: {e}")
        return 1

    try:
        with conn.cursor() as cur:
            # Example schema evolution: add a nullable profile column if missing
            cur.execute(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS profile JSONB;
                """
            )
            conn.commit()
        print("Migration completed successfully.")
        return 0
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())



