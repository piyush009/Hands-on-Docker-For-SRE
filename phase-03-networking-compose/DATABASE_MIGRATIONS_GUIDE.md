# Database Migrations in Containerized Environments - Comprehensive Guide

## Overview

This guide elaborates on handling database migrations in containerized environments, covering patterns, best practices, and real-world implementation strategies based on Phase 3 and Phase 4 examples.

---

## Common Migration Patterns

### 1. Init Scripts Pattern (PostgreSQL `/docker-entrypoint-initdb.d/`)

**How it works:**
- PostgreSQL official image automatically runs any `.sql`, `.sh`, or `.sql.gz` files found in `/docker-entrypoint-initdb.d/` directory
- These scripts execute **only on first initialization** (when data directory is empty)
- Perfect for initial schema setup, seed data, or one-time initialization

**Implementation Example:**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d  # Mount init scripts
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppass
```

```sql
-- init-scripts/01-schema.sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- init-scripts/02-seed-data.sql
INSERT INTO users (username, email) VALUES 
    ('admin', 'admin@example.com'),
    ('demo', 'demo@example.com');
```

**When to use:**
- ✅ Initial database setup
- ✅ Seed data for development/staging
- ✅ One-time initialization scripts
- ❌ NOT for ongoing schema changes (only runs once)

**Pros:**
- Simple and automatic
- No additional tooling needed
- Works out-of-the-box with PostgreSQL image

**Cons:**
- Only runs on first initialization
- Can't handle incremental migrations
- No version tracking

---

### 2. Migration Tool in App Startup Pattern

**How it works:**
- Application code includes migration tooling (e.g., Flask-Migrate/Alembic, Django migrations, Rails migrations)
- Migrations run automatically when the application starts
- Common in frameworks that have built-in migration support

**Implementation Example (Flask with Alembic):**

```python
# app.py
from flask import Flask
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

# Initialize database and migrations
db.init_app(app)
migrate = Migrate(app, db)

# Run migrations on startup (optional - can be done separately)
@app.before_first_request
def create_tables():
    db.create_all()
    # Or: migrate.upgrade() for Alembic
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install flask flask-migrate alembic
COPY . .
CMD ["python", "app.py"]  # Migrations run as part of app startup
```

**When to use:**
- ✅ Framework-native migrations (Django, Rails, Flask-Migrate)
- ✅ Small to medium applications
- ✅ When migrations are tightly coupled to application code
- ✅ Development environments

**Pros:**
- Integrated with application framework
- Version tracking built-in
- Easy to manage alongside code

**Cons:**
- App startup depends on migration success
- Can slow down deployments
- Risk of running migrations multiple times if not idempotent
- Harder to separate migration concerns from application logic

**Best Practice:**
Make migrations idempotent and check migration status before running:
```python
# Check if migration needed before running
if not migration.is_up_to_date():
    migration.upgrade()
```

---

### 3. Separate Migration Container Pattern (Recommended for Production)

**How it works:**
- Create a dedicated migration service/job in docker-compose
- Run migrations as a one-off container that exits after completion
- Separate from application containers - can be run independently

**Implementation Example (Phase 4 Pattern):**

```yaml
# docker-compose.yml
services:
  web:
    build: .
    # ... web service config
    depends_on:
      db:
        condition: service_healthy
  
  db:
    image: postgres:15-alpine
    # ... db service config
  
  migrator:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["python", "migrate.py"]
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: appdb
      DB_USER: appuser
      DB_PASSWORD: apppass
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network
    restart: "no"  # One-off job, don't restart
```

```python
# migrate.py (Phase 4 example)
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
    print("Running migration...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Idempotent migration
            cur.execute("""
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS profile JSONB;
            """)
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
```

**Running migrations:**
```bash
# Run migration as one-off job
docker compose run --rm migrator

# Or in production CI/CD
docker compose -f docker-compose.prod.yml run --rm migrator
```

**When to use:**
- ✅ Production environments
- ✅ CI/CD pipelines
- ✅ When you need control over when migrations run
- ✅ Multi-service architectures
- ✅ When migrations should be separate from app deployment

**Pros:**
- Clear separation of concerns
- Can run migrations independently of app deployment
- Easy to integrate into CI/CD pipelines
- Can test migrations separately
- Better for rollback scenarios

**Cons:**
- Requires additional service definition
- Need to ensure migrations run before app updates
- More complex orchestration

**Best Practice - Migration Workflow:**
```bash
# 1. Backup database first
docker compose exec db pg_dump -U appuser appdb > backup.sql

# 2. Run migration
docker compose run --rm migrator

# 3. Verify migration success
docker compose exec db psql -U appuser -d appdb -c "\d users"

# 4. Deploy new app version
docker compose up -d --build web
```

---

### 4. CI/CD Pipeline Pattern

**How it works:**
- Migrations run as a separate step in CI/CD pipeline
- Typically runs before deploying new application version
- Can use same migration container or dedicated migration job

**Implementation Example (GitHub Actions / GitLab CI):**

```yaml
# .github/workflows/deploy.yml
name: Deploy Application

on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run database migrations
        run: |
          docker compose -f docker-compose.prod.yml run --rm migrator
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  
  deploy:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy application
        run: |
          docker compose -f docker-compose.prod.yml up -d --build web
```

**When to use:**
- ✅ Production deployments
- ✅ Automated release pipelines
- ✅ When you want migrations as explicit deployment step
- ✅ Multi-environment deployments (dev → staging → prod)

**Pros:**
- Automated and repeatable
- Can gate deployments on migration success
- Audit trail in CI/CD logs
- Can run tests after migrations

**Cons:**
- Requires CI/CD infrastructure
- More complex setup
- Need to handle secrets securely

---

## Best Practices for All Patterns

### 1. Idempotent Migrations

**Always make migrations safe to run multiple times:**

```sql
-- ✅ Good: Idempotent
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile JSONB;
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ❌ Bad: Not idempotent
ALTER TABLE users ADD COLUMN profile JSONB;  -- Fails if column exists
```

**Python example:**
```python
# Check if migration already applied
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='users' AND column_name='profile'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE users ADD COLUMN profile JSONB;")
```

### 2. Version Tracking

**Track which migrations have been applied:**

```sql
-- Create migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Record migration
INSERT INTO schema_migrations (version) 
VALUES ('001_add_profile_column')
ON CONFLICT (version) DO NOTHING;
```

### 3. Test in Staging First

**Always test migrations on staging environment with realistic data:**

```bash
# Staging workflow
docker compose -f docker-compose.staging.yml run --rm migrator
docker compose -f docker-compose.staging.yml up -d --build web

# Run integration tests
pytest tests/integration/

# Only then promote to production
```

### 4. Rollback Procedures

**Have a plan to rollback migrations:**

```python
# migrate.py with rollback support
def rollback():
    """Rollback the migration"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Remove the column we added
            cur.execute("""
                ALTER TABLE users 
                DROP COLUMN IF EXISTS profile;
            """)
            conn.commit()
        print("Rollback completed.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Rollback failed: {e}")
    finally:
        conn.close()
```

**Run rollback:**
```bash
docker compose run --rm migrator python migrate.py --rollback
```

### 5. Backup Before Migrations

**Always backup before running migrations in production:**

```bash
# Backup script
#!/bin/bash
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker compose exec db pg_dump -U appuser appdb > "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"

# Run migration
docker compose run --rm migrator

# If migration fails, restore
if [ $? -ne 0 ]; then
    echo "Migration failed, restoring backup..."
    docker compose exec -T db psql -U appuser appdb < "$BACKUP_FILE"
fi
```

### 6. Backward Compatibility

**Design migrations to be backward compatible when possible:**

```sql
-- ✅ Good: Add nullable column (old app still works)
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile JSONB;

-- Later: Make it required after app is updated
-- ALTER TABLE users ALTER COLUMN profile SET NOT NULL;

-- ❌ Bad: Breaking change immediately
ALTER TABLE users DROP COLUMN email;  -- Breaks old app version
```

### 7. Migration Timeouts and Monitoring

**Set timeouts and monitor migration progress:**

```python
import signal
import sys

def timeout_handler(signum, frame):
    print("Migration timeout!")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minute timeout

try:
    # Run migration
    run_migration()
finally:
    signal.alarm(0)  # Cancel timeout
```

---

## Real-World Scenarios & Solutions

### Scenario 1: Zero-Downtime Migration

**Challenge:** Need to add a column without stopping the application.

**Solution - Expand-and-Contract Pattern:**

```sql
-- Step 1: Add nullable column (compatible with old app)
ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field VARCHAR(100);

-- Step 2: Deploy new app version that writes to both old and new fields
-- (Application code handles both)

-- Step 3: Backfill data (run in batches)
UPDATE users SET new_field = old_field WHERE new_field IS NULL;

-- Step 4: Make column NOT NULL (after all data migrated)
ALTER TABLE users ALTER COLUMN new_field SET NOT NULL;

-- Step 5: Remove old column (in future migration)
-- ALTER TABLE users DROP COLUMN old_field;
```

### Scenario 2: Large Table Migration

**Challenge:** Adding index to large table locks table for too long.

**Solution - Concurrent Index Creation:**

```sql
-- PostgreSQL: Create index concurrently (doesn't lock table)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email 
ON users(email);

-- MySQL: Use online DDL
ALTER TABLE users ADD INDEX idx_users_email (email), ALGORITHM=INPLACE, LOCK=NONE;
```

### Scenario 3: Multi-Service Migration Coordination

**Challenge:** Multiple services need to coordinate during migration.

**Solution - Feature Flags + Gradual Rollout:**

```python
# Migration script with feature flag
def migrate_with_feature_flag():
    # Enable feature flag in database
    set_feature_flag('new_schema', enabled=False)
    
    # Run migration
    run_migration()
    
    # Enable feature flag gradually
    set_feature_flag('new_schema', enabled=True, rollout_percent=10)
    
    # Monitor, then increase rollout
    # set_feature_flag('new_schema', enabled=True, rollout_percent=100)
```

---

## Comparison Matrix

| Pattern | Complexity | Production Ready | Version Tracking | Rollback Support | Best For |
|---------|-----------|------------------|-------------------|------------------|----------|
| Init Scripts | Low | ❌ | ❌ | ❌ | Initial setup only |
| App Startup | Medium | ⚠️ | ✅ | ⚠️ | Small apps, dev |
| Separate Container | Medium | ✅ | ✅ | ✅ | Production, CI/CD |
| CI/CD Pipeline | High | ✅ | ✅ | ✅ | Enterprise, multi-env |

---

## Interview Talking Points

### Key Points to Mention:

1. **"I use idempotent migrations"**
   - Explain how you use `IF NOT EXISTS`, `IF EXISTS` clauses
   - Mention checking migration state before applying

2. **"I test migrations in staging first"**
   - Describe staging environment with production-like data
   - Mention performance testing migrations on large datasets

3. **"I have rollback procedures"**
   - Explain how you design reversible migrations
   - Mention backup/restore as fallback

4. **"I separate migration concerns from application deployment"**
   - Explain why separate migration containers are better
   - Mention CI/CD integration

5. **"I use backward-compatible migration strategies"**
   - Explain expand-and-contract pattern
   - Mention zero-downtime deployment considerations

6. **"I monitor and set timeouts"**
   - Explain how you handle long-running migrations
   - Mention alerting on migration failures

### Example Interview Answer:

> "In containerized environments, I handle database migrations using a separate migration container pattern. This gives me control over when migrations run, separate from application deployments. 
>
> I make all migrations idempotent using `IF NOT EXISTS` clauses and version tracking tables. Before running migrations in production, I always test them in staging with realistic data volumes, and I create backups first.
>
> In CI/CD, migrations run as a separate job before deploying the new application version. If a migration fails, I have rollback scripts ready, and I can restore from the backup if needed.
>
> For zero-downtime scenarios, I use the expand-and-contract pattern - adding new columns as nullable first, then backfilling data, and only making them required after the new app version is deployed. This allows old and new app versions to run side-by-side during the transition."

---

## References

- Phase 3: Basic multi-container setup with PostgreSQL
- Phase 4: Migration container pattern implementation (`migrate.py`)
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Docker Compose Documentation: https://docs.docker.com/compose/

