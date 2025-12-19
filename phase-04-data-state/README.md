## Phase 4 – Data & State Management (Volumes, Backups, Migrations)

**Goal**: Think like an SRE about **stateful workloads**: how containers handle data, how you persist it, back it up, migrate it, and upgrade schemas safely.

We’ll extend the **Flask + PostgreSQL** idea and focus on:
- Volumes vs bind mounts and when to use which.
- Backups and restore patterns with Docker.
- Database migrations and zero/minimal downtime upgrade stories.
- Real-world failure modes and how to talk about them in interviews.

---

## 1. Project Structure

This phase lives in `phase-04-data-state/`:

```text
phase-04-data-state/
├── app.py              # Flask app (reads/writes users + extra profile data)
├── migrate.py          # Simple migration script (simulates schema upgrade)
├── requirements.txt    # Python deps (Flask + psycopg2)
├── Dockerfile          # Image for web + migration job
├── docker-compose.yml  # Web + DB + migration service
└── README.md           # This file
```

We will:
- Start with a simple schema.
- Run the app and insert data.
- Run a **migration container** to upgrade schema.
- Observe data survives container restarts and upgrades via **named volumes**.

---

## 2. Volumes vs Bind Mounts – Mental Model

- **Named volumes**:
  - Managed by Docker (under `/var/lib/docker/volumes/...`).
  - Great for **production-like** database/data persistence.
  - Portable between hosts with explicit backup/restore.
  - Docker handles permissions and lifecycle.

- **Bind mounts**:
  - Map a **host directory** into the container.
  - Great for **development** (live code editing, inspecting files).
  - Can cause permission issues and tightly couple container to host paths.

In this phase, we use a **named volume** for PostgreSQL data, and briefly show how you would use bind mounts for backups or debugging.

---

## 3. Compose Stack Overview

Open `docker-compose.yml`. You’ll see three services:

- **`db`** – PostgreSQL:
  - Uses `postgres:15-alpine`.
  - Stores data in a named volume `phase4_postgres_data`.

- **`web`** – Flask app:
  - Same pattern as Phase 3, but with an extra `profile` column and endpoint.
  - Connects to `db` via Docker network, uses env vars for credentials.

- **`migrator`** – one-off migration job:
  - Uses the same image as `web`.
  - Runs `python migrate.py` and **exits**.
  - Can be run on demand to upgrade schema.

Named volumes:

```yaml
volumes:
  phase4_postgres_data:
    driver: local
```

**Key idea**: You can destroy and recreate containers freely, but as long as you reuse the **same volume**, the database data persists.

---

## 4. Run the Stack and See Persistence

From `phase-04-data-state/`:

### 4.1. Start DB and Web

```bash
docker compose up --build web db
```

Wait until both are up:

```bash
docker compose ps
```

You should see `phase4-web` and `phase4-db` running.

### 4.2. Insert Data

Call the app (easiest with browser or curl):

```bash
curl http://localhost:8082/healthz

curl -X POST http://localhost:8082/users \
  -H "Content-Type: application/json" \
  -d '{"username": "phase4_user", "email": "p4@example.com"}'
```

List users:

```bash
curl http://localhost:8082/users
```

### 4.3. Restart Containers – Data Persists

Stop and start again:

```bash
docker compose down         # containers + network removed, volume kept
docker compose up web db    # recreate containers
```

Check users again:

```bash
curl http://localhost:8082/users
```

**You should still see the data** – proof that named volumes preserve state across container lifecycles.

---

## 5. Simulated Schema Upgrade with Migration Container

Our initial schema has a basic `users` table. We’ll **evolve** it by adding a `profile` JSON field (or similar) using `migrate.py`.

### 5.1. Run Migration

With `db` running, execute the migration job:

```bash
docker compose run --rm migrator
```

What this does:
- Starts a temporary container from the same image as `web`.
- Runs `python migrate.py`.
- Connects to the same database (`db`) and **alters the schema**.
- Exits and is removed (`--rm`).

### 5.2. Verify New Schema

From the `web` API:

```bash
curl http://localhost:8082/users
```

You should still see existing users, but now the schema supports an additional `profile` field. You can extend `app.py` to update or display this profile.

From inside the DB:

```bash
docker compose exec db psql -U appuser -d appdb

-- Inside psql:
\d users
SELECT * FROM users;
\q
```

You’ll see the extra column added by the migration script.

---

## 6. Backups & Restore with Volumes

In real SRE work, you must be comfortable explaining **how to back up and restore** Dockerized databases.

### 6.1. Backup with `pg_dump`

Create a backup directory on host (from `phase-04-data-state/`):

```bash
mkdir -p backups
```

Create a logical backup:

```bash
docker compose exec db \
  pg_dump -U appuser -d appdb -F c -f /tmp/appdb.backup

docker compose exec db \
  sh -c "cat /tmp/appdb.backup" > backups/appdb.backup
```

Now you have `backups/appdb.backup` on your host.

### 6.2. Simulate Disaster and Restore

Simulate data loss by dropping the volume:

```bash
docker compose down -v   # ⚠️ removes containers + volumes
docker volume ls         # volume for phase4 should be gone
```

Recreate stack:

```bash
docker compose up -d db
```

Create an **empty** database and restore:

```bash
docker compose exec db \
  createdb -U appuser appdb_restored || true

cat backups/appdb.backup | docker compose exec -T db \
  pg_restore -U appuser -d appdb_restored
```

Check restored data:

```bash
docker compose exec db psql -U appuser -d appdb_restored -c "SELECT * FROM users;"
```

**Key interview point**: You understand the difference between:
- **Logical backup** (e.g., `pg_dump`, `mysqldump`) – schema + data, independent of underlying storage.
- **Volume-level backup** (e.g., `tar` the volume) – raw filesystem backup, faster but more coupled.

---

## 7. Bind Mount Example (For Dev / Debug)

To inspect database files directly (for debugging only), you might temporarily use a bind mount instead of a named volume, mapping a host directory to `/var/lib/postgresql/data`.

**But** this is often OS/permissions-sensitive and not recommended for production.

**Example pattern (conceptual):**

```yaml
volumes:
  - ./local_pgdata:/var/lib/postgresql/data
```

Then you can inspect `./local_pgdata` on your host. In interviews, emphasize you:
- Prefer **named volumes** or managed DBs for production.
- Use bind mounts mostly for **local debugging**.

---

## 8. Interview POV – Questions and Answers (Phase 4)

### Volumes & Persistence

- **Q: Why shouldn’t you store database data inside the container filesystem (without volumes)?**  
  **A:** Because container filesystems are **ephemeral**. If the container is removed or rescheduled, the data is lost. Using volumes or external storage decouples data from container lifecycle, which is critical for reliability and recoverability.

- **Q: Compare Docker named volumes vs bind mounts. When would you use each?**  
  **A:** Named volumes are Docker-managed, portable, and good for production data (databases, queues). Bind mounts map host paths and are best for development (live code edits, quick inspection). Bind mounts can cause portability and permission problems in production, so I prefer named volumes or external storage for critical state.

- **Q: What happens to volume data when you run `docker compose down` vs `docker compose down -v`?**  
  **A:** `docker compose down` removes containers and networks but **keeps volumes** (data persists). `docker compose down -v` also removes volumes, so data is deleted. In production, you must be very careful with `-v` to avoid accidental data loss.

### Backups & Restores

- **Q: How would you back up a database running in a Docker container?**  
  **A:** For relational DBs, I prefer **logical backups** using tools like `pg_dump` or `mysqldump` inside the container, streaming output to host or object storage (S3, GCS). For some workloads, I also use **volume-level snapshots** or cloud provider volume snapshots. Key points: automate backups, store them off-host, encrypt when needed, and regularly **test restore**.

- **Q: How do you restore from a Dockerized database backup?**  
  **A:** Spin up a DB container (possibly a separate restore environment), create an empty database, then pipe the backup into restore tools like `pg_restore` or `psql`. For volume-level backups, recreate volume from snapshot. I emphasize that I’ve actually **tested restore procedures**, not just backups.

- **Q: What’s your strategy to avoid data loss during container upgrades?**  
  **A:** Never tie data to container lifecycle. Use persistent volumes, avoid destructive `down -v` commands in production, and ensure backups are current before upgrades. I also plan for rollback by keeping previous image versions and validating schema migrations.

### Migrations & Upgrades

- **Q: How do you handle database schema changes in a containerized environment?**  
  **A:** Use a migration strategy: versioned migration scripts (e.g., Alembic, Flyway), and run them via dedicated migration jobs/containers as part of deployment. Ensure migrations are **idempotent** and backward-compatible where possible, run them against staging first, and have a rollback plan. Containers help by packaging migration tooling with the app.

- **Q: What patterns can you use to minimize downtime during schema migrations?**  
  **A:**  
  - Use **expand-and-contract**: add new columns first, migrate data, update app to write to both schemas, then remove old fields later.  
  - Perform migrations that are safe while old and new app versions run side by side.  
  - Use **read-only windows** or short maintenance windows for heavy migrations.  
  - Blue-green or canary deployments with DB-compatible versions.

- **Q: What can go wrong during a migration and how do you mitigate it?**  
  **A:** Issues include long-running locks, failed migrations leaving schema half-applied, and incompatible app/DB versions. I mitigate by: testing migrations on realistic data, adding timeouts, ensuring migrations are **re-runnable**, backing up before major migrations, and designing changes to be backward-compatible when possible.

### Real-World / Behavioral

- **Q: Tell me about a time you recovered from data loss or corruption.**  
  **A:** A strong answer describes: how you detected the issue (alerts, logs), how you verified scope, what backup you chose, how you restored (steps + verification), and what you changed afterward (alerts, backup frequency, permissions, process). Tie in Docker if relevant (volumes, snapshots, container orchestration).

- **Q: How do you decide whether to run a database inside Docker or use a managed service?**  
  **A:** For serious production systems, I usually prefer **managed databases** (RDS, Cloud SQL) because they handle backups, HA, failover, and patching. Running DBs in Docker can be fine for dev/staging or smaller apps, but then I need to design storage, backup, monitoring, and HA myself. I weigh complexity vs control and team expertise.

---

## 9. Real-World Challenges & Talking Points (Phase 4)

- **Accidental `down -v` in production-like environments**  
  - Challenge: An engineer runs `docker compose down -v` and wipes volumes.  
  - Talking point: Emphasize how you introduced safeguards (read-only roles, clear docs, separate dev/prod compose files, backup + restore drills).

- **Migrations that work in dev but fail on real data**  
  - Challenge: Dev DB is tiny and clean; prod DB has edge cases and large tables.  
  - Talking point: You added staging environments with realistic data, performance-tested migrations, added timeouts and progress monitoring, and made migrations resumable.

- **Cross-region or cross-cluster restores**  
  - Challenge: Need to restore backups to a different region or new cluster.  
  - Talking point: You practiced DR (disaster recovery) drills: restoring logical backups into a fresh cluster, validating app connectivity, and documenting RPO/RTO.

---

## 10. When You’re Comfortable

You are ready to move on when you can:
- Clearly explain and choose between volumes, bind mounts, and external storage.
- Demonstrate a full backup + restore workflow for a containerized database.
- Describe robust database migration and upgrade strategies.
- Tell a convincing story about handling data-related incidents and learning from them.

Next is **Phase 5 – Observability, Health, and Debugging**, where we’ll focus on logs, metrics, health checks, and real-world troubleshooting stories that SRE interviewers love to dig into.



