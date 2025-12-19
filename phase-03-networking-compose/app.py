#!/usr/bin/env python3
"""
Phase 3 Flask App - Connects to PostgreSQL database
Demonstrates Docker networking and multi-container orchestration
"""

import os
import psycopg2
from flask import Flask, jsonify
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Database connection parameters from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),  # Service name in docker-compose
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'appdb'),
    'user': os.getenv('DB_USER', 'appuser'),
    'password': os.getenv('DB_PASSWORD', 'apppass'),
}


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        app.logger.error(f"Database connection error: {e}")
        return None


def init_db():
    """Initialize database schema if it doesn't exist."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            # Create users table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Insert a sample user if table is empty
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("""
                    INSERT INTO users (username, email) 
                    VALUES ('demo_user', 'demo@example.com')
                """)
                conn.commit()
        return True
    except psycopg2.Error as e:
        app.logger.error(f"Database initialization error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


@app.route('/')
def index():
    """Root endpoint - shows app info."""
    return jsonify({
        'service': 'phase3-flask-db',
        'phase': 3,
        'description': 'Multi-container app with PostgreSQL',
        'endpoints': {
            '/healthz': 'Health check endpoint',
            '/users': 'List all users from database'
        }
    })


@app.route('/healthz')
def healthz():
    """Health check endpoint."""
    conn = get_db_connection()
    db_status = 'healthy' if conn else 'unhealthy'
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
            conn.close()
        except psycopg2.Error:
            db_status = 'unhealthy'
    
    return jsonify({
        'status': 'ok' if db_status == 'healthy' else 'degraded',
        'database': db_status,
        'service': 'phase3-web'
    }), 200 if db_status == 'healthy' else 503


@app.route('/users')
def get_users():
    """Fetch all users from database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({
            'error': 'Database connection failed',
            'users': []
        }), 503
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, username, email, created_at FROM users ORDER BY id')
            users = cur.fetchall()
            return jsonify({
                'count': len(users),
                'users': [dict(user) for user in users]
            }), 200
    except psycopg2.Error as e:
        app.logger.error(f"Query error: {e}")
        return jsonify({
            'error': 'Database query failed',
            'details': str(e)
        }), 500
    finally:
        conn.close()


if __name__ == '__main__':
    # Initialize database on startup
    app.logger.info("Initializing database...")
    if init_db():
        app.logger.info("Database initialized successfully")
    else:
        app.logger.warning("Database initialization failed - app will still start")
    
    # Run Flask app
    # Bind to 0.0.0.0 to accept connections from Docker network
    app.run(host='0.0.0.0', port=5000, debug=False)

