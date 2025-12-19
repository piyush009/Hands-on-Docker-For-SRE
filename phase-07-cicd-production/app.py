#!/usr/bin/env python3
"""
Phase 7 Flask App - Production-ready with CI/CD
Same as Phase 6, demonstrating production deployment patterns.
"""

import os
import time
import json
import logging
from datetime import datetime
from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'service': 'phase7-web',
            'version': os.getenv('APP_VERSION', 'unknown'),
            'message': record.getMessage(),
        }
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'path'):
            log_entry['path'] = record.path
        if hasattr(record, 'status'):
            log_entry['status'] = record.status
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        if hasattr(record, 'error'):
            log_entry['error'] = record.error
        return json.dumps(log_entry)

logger = logging.getLogger('phase7-web')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

app = Flask(__name__)

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_errors_total = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'status']
)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'appdb'),
    'user': os.getenv('DB_USER', 'appuser'),
    'password': os.getenv('DB_PASSWORD', 'apppass'),
}

db_ready = False


def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        logger.error('Database connection error', extra={'error': str(e)})
        return None


def init_db():
    global db_ready
    conn = get_db_connection()
    if not conn:
        db_ready = False
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            db_ready = True
            logger.info('Database initialized successfully')
            return True
    except psycopg2.Error as e:
        logger.error('Database initialization error', extra={'error': str(e)})
        conn.rollback()
        db_ready = False
        return False
    finally:
        conn.close()


@app.before_request
def before_request():
    request.start_time = time.time()


@app.after_request
def after_request(response):
    duration_ms = (time.time() - request.start_time) * 1000
    
    http_requests_total.labels(
        method=request.method,
        endpoint=request.endpoint or request.path,
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.endpoint or request.path
    ).observe(duration_ms / 1000)
    
    if response.status_code >= 400:
        http_errors_total.labels(
            method=request.method,
            endpoint=request.endpoint or request.path,
            status=response.status_code
        ).inc()
    
    logger.info(
        'Request processed',
        extra={
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_ms': round(duration_ms, 2)
        }
    )
    
    return response


@app.route('/')
def index():
    return jsonify({
        'service': 'phase7-flask-production',
        'phase': 7,
        'version': os.getenv('APP_VERSION', 'dev'),
        'build_date': os.getenv('BUILD_DATE', 'unknown'),
        'git_sha': os.getenv('GIT_SHA', 'unknown'),
        'description': 'CI/CD and production deployment demo',
        'endpoints': {
            '/healthz': 'Liveness probe',
            '/readyz': 'Readiness probe',
            '/metrics': 'Prometheus metrics',
            '/users': 'List users from database',
            '/version': 'Version information'
        }
    })


@app.route('/version')
def version():
    """Version endpoint for deployment tracking."""
    return jsonify({
        'version': os.getenv('APP_VERSION', 'dev'),
        'build_date': os.getenv('BUILD_DATE', 'unknown'),
        'git_sha': os.getenv('GIT_SHA', 'unknown'),
        'environment': os.getenv('APP_ENV', 'unknown')
    }), 200


@app.route('/healthz')
def healthz():
    return jsonify({
        'status': 'healthy',
        'service': 'phase7-web',
        'version': os.getenv('APP_VERSION', 'dev'),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@app.route('/readyz')
def readiness():
    global db_ready
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
            conn.close()
            db_ready = True
            return jsonify({
                'status': 'ready',
                'service': 'phase7-web',
                'database': 'connected',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 200
        except psycopg2.Error as e:
            logger.error('Readiness check failed', extra={'error': str(e)})
            db_ready = False
            return jsonify({
                'status': 'not ready',
                'service': 'phase7-web',
                'database': 'disconnected',
                'error': str(e)
            }), 503
    else:
        db_ready = False
        return jsonify({
            'status': 'not ready',
            'service': 'phase7-web',
            'database': 'disconnected'
        }), 503


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/users')
def get_users():
    conn = get_db_connection()
    if not conn:
        logger.error('Database connection failed', extra={'endpoint': '/users'})
        return jsonify({
            'error': 'Database connection failed',
            'users': []
        }), 503
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, username, email, created_at FROM users ORDER BY id')
            users = cur.fetchall()
            logger.info('Users fetched successfully', extra={'count': len(users)})
            return jsonify({
                'count': len(users),
                'users': [dict(user) for user in users]
            }), 200
    except psycopg2.Error as e:
        logger.error('Database query error', extra={'error': str(e), 'endpoint': '/users'})
        return jsonify({
            'error': 'Database query failed',
            'details': str(e)
        }), 500
    finally:
        conn.close()


if __name__ == '__main__':
    logger.info('Starting application...', extra={'version': os.getenv('APP_VERSION', 'dev')})
    if init_db():
        logger.info('Application started successfully')
    else:
        logger.warning('Database initialization failed - app will still start')
    
    app.run(host='0.0.0.0', port=5000, debug=False)

