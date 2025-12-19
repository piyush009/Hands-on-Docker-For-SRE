#!/usr/bin/env python3
"""
Phase 4 Flask App - Focus on stateful behavior and schema evolution.
"""

import os
from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "appdb"),
    "user": os.getenv("DB_USER", "appuser"),
    "password": os.getenv("DB_PASSWORD", "apppass"),
}


def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        app.logger.error(f"DB connection error: {e}")
        return None


def init_db():
    """
    Initial schema: users table without profile column.
    Migration script can add extra columns later.
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()
        return True
    except psycopg2.Error as e:
        app.logger.error(f"DB init error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


@app.route("/")
def index():
    return jsonify(
        {
            "service": "phase4-flask-db",
            "phase": 4,
            "description": "Stateful app with schema evolution focus",
            "endpoints": {
                "/healthz": "Health check",
                "/users": "GET list users, POST create user",
            },
        }
    )


@app.route("/healthz")
def healthz():
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "db_unreachable"}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({"status": "ok"}), 200
    except psycopg2.Error:
        return jsonify({"status": "db_error"}), 503
    finally:
        conn.close()


@app.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username")
        email = data.get("email")
        if not username:
            return jsonify({"error": "username is required"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "db_unreachable"}), 503

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id",
                    (username, email),
                )
                user_id = cur.fetchone()[0]
                conn.commit()
            return jsonify({"id": user_id, "username": username, "email": email}), 201
        except psycopg2.Error as e:
            conn.rollback()
            app.logger.error(f"Insert error: {e}")
            return jsonify({"error": "insert_failed", "details": str(e)}), 500
        finally:
            conn.close()

    # GET
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "db_unreachable"}), 503

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, username, email, created_at FROM users ORDER BY id")
            rows = cur.fetchall()
        return jsonify({"count": len(rows), "users": [dict(r) for r in rows]}), 200
    except psycopg2.Error as e:
        app.logger.error(f"Select error: {e}")
        return jsonify({"error": "query_failed", "details": str(e)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.logger.info("Initializing DB (Phase 4)...")
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)



