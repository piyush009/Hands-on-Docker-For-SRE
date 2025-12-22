## Phase 3 – Docker Networking & Docker Compose (Multi-Container Apps)

**Goal**: Understand Docker networking, how containers communicate, and use `docker-compose` to orchestrate multi-service applications (web + database). This is essential for real-world SRE work.

We'll build a **Flask web app** that connects to a **PostgreSQL database**, orchestrated with Docker Compose.

---

## 1. Prerequisites

- Completed Phase 1 and Phase 2.
- Docker Desktop running.
- Basic understanding of databases (you don't need to be a DBA).

---

## 2. Project Structure

```
phase-03-networking-compose/
├── app.py              # Flask app that queries PostgreSQL
├── requirements.txt    # Python dependencies (includes psycopg2)
├── Dockerfile          # Dockerfile for the web app
├── docker-compose.yml  # Orchestration file
└── README.md           # This file
```

---

## 3. Understanding Docker Networking

### 3.1. Default Networks

Docker creates three default networks:

```bash
docker network ls
```

You'll see:
- `bridge` (default) – containers on this can communicate by IP
- `host` – container shares host's network stack
- `none` – no networking

### 3.2. User-Defined Networks

When you use `docker-compose`, it creates a **user-defined bridge network** automatically. Containers on the same network can reach each other by **service name** (DNS resolution).

**Key concept**: In `docker-compose.yml`, services can reference each other by their service name. For example, if you have a service named `db`, your app can connect to `db:5432` instead of an IP address.

---

## 4. The Application

Our Flask app (`app.py`) will:
- Connect to PostgreSQL using environment variables.
- Expose a `/users` endpoint that queries the database.
- Have a `/healthz` endpoint for health checks.

The database will:
- Use the official PostgreSQL image.
- Persist data using a Docker volume.
- Be initialized with a simple schema.

---

## 5. Docker Compose File Explained

Open `docker-compose.yml` and understand:

### 5.1. Services

- **`web`**: Our Flask application
  - Builds from `Dockerfile` in current directory
  - Depends on `db` (waits for database to be ready)
  - Exposes port `8080` on host → `5000` in container
  - Uses environment variables from `.env` file (or inline)

- **`db`**: PostgreSQL database
  - Uses official `postgres:15-alpine` image
  - Sets environment variables for database name, user, password
  - Creates a named volume `postgres_data` for persistence
  - Exposes port `5432` (only for debugging; web connects via internal network)

### 5.2. Networks

- Docker Compose creates a default network automatically.
- Both services are on the same network, so `web` can reach `db` by name.

### 5.3. Volumes

- `postgres_data`: Named volume for database persistence (survives container restarts).

---

## 6. Hands-On: Build and Run

### 6.1. Start Everything

From `phase-03-networking-compose/` directory:

```bash
docker-compose up --build
```

**What happens:**
- Docker Compose reads `docker-compose.yml`
- Creates a network (e.g., `phase-03-networking-compose_default`)
- Creates volume `postgres_data` (if it doesn't exist)
- Builds the `web` image
- Starts `db` container
- Waits for `db` to be healthy (if healthcheck configured)
- Starts `web` container

### 6.2. Test the Application

In another terminal:

```bash
# Check running containers
docker-compose ps

# View logs from all services
docker-compose logs

# View logs from specific service
docker-compose logs web
docker-compose logs db
```

Visit in browser:
- `http://localhost:8080/healthz` – should return health status
- `http://localhost:8080/users` – should query database (may be empty initially)

### 6.3. Exec into Containers

```bash
# Exec into web container
docker-compose exec web /bin/sh

# Exec into db container
docker-compose exec db psql -U appuser -d appdb

# Inside psql, try:
# SELECT * FROM users;
# \q to exit
```

### 6.4. Stop Everything

```bash
# Stop containers (keeps volumes)
docker-compose down

# Stop and remove volumes (⚠️ deletes database data)
docker-compose down -v
```

---

## 7. Networking Deep Dive

### 7.1. Inspect the Network

```bash
# List networks
docker network ls

# Inspect the compose network
docker network inspect phase-03-networking-compose_default
```

You'll see:
- Containers attached to the network
- IP addresses assigned
- Gateway and subnet information

### 7.2. Test Container-to-Container Communication

```bash
# From web container, ping db
docker-compose exec web getent hosts db

# From web container, test PostgreSQL connection
docker-compose exec web python -c 'import psycopg2; conn = psycopg2.connect(host="db", dbname="appdb", user="appuser", password="apppass"); print("Connected!")'
```

### 7.3. Connect External Container to Compose Network

```bash
# Run a temporary container on the same network
docker run --rm -it --network phase-03-networking-compose_default alpine ping -c 3 db
```

---

## 8. Volume Management

### 8.1. List Volumes

```bash
docker volume ls
```

You should see `phase-03-networking-compose_postgres_data`.

### 8.2. Inspect Volume

```bash
docker volume inspect phase-03-networking-compose_postgres_data
```

### 8.3. Backup Volume Data

```bash
# Create a backup
docker run --rm -v phase-03-networking-compose_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore (example)
# docker run --rm -v phase-03-networking-compose_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

---

## 9. Environment Variables

### 9.1. Using `.env` File

Create a `.env` file (not committed to git):

```env
POSTGRES_DB=appdb
POSTGRES_USER=appuser
POSTGRES_PASSWORD=apppass
WEB_PORT=8080
```

Then reference in `docker-compose.yml`:

```yaml
environment:
  POSTGRES_DB: ${POSTGRES_DB}
```

### 9.2. Override at Runtime

```bash
POSTGRES_PASSWORD=newpass docker-compose up
```

---

## 10. Common docker-compose Commands

```bash
# Start in detached mode
docker-compose up -d

# Rebuild and restart
docker-compose up --build -d

# Scale a service (if stateless)
docker-compose up -d --scale web=3

# View logs (follow)
docker-compose logs -f web

# Execute command in service
docker-compose exec web python -c "print('hello')"

# Restart a service
docker-compose restart web

# Stop all services
docker-compose stop

# Remove containers and networks
docker-compose down

# Remove everything including volumes
docker-compose down -v
```

---

## 11. Interview POV – Questions from This Phase

### **Conceptual**

**Q: What is the difference between `bridge`, `host`, and `none` network modes in Docker?**

**A:**
- **`bridge`** (default): Containers get their own network namespace with an IP on a virtual bridge. Containers can communicate by IP, and port mapping (`-p`) exposes ports to the host. This is the most common mode.
- **`host`**: Container shares the host's network stack directly. No isolation, no port mapping needed. Faster but less secure. Useful for high-performance scenarios.
- **`none`**: Container has no network interfaces. Completely isolated. Rarely used except for security-sensitive workloads.

**Q: How does DNS resolution work between containers in Docker Compose?**

**A:** Docker Compose creates a user-defined bridge network and runs an embedded DNS server. Each service name becomes a DNS name. When container A tries to connect to `db:5432`, Docker's DNS resolves `db` to the IP of the `db` service container. This works automatically on the same network – no need to hardcode IPs.

**Q: What is the difference between a named volume and a bind mount?**

**A:**
- **Named volume**: Managed by Docker, stored in Docker's directory (usually `/var/lib/docker/volumes/`). Portable, works across platforms, good for databases and persistent data. Docker handles permissions.
- **Bind mount**: Maps a host directory directly into the container. Useful for development (live code reload), but ties the container to host filesystem structure. Less portable.

**Q: Explain the `depends_on` directive in docker-compose.yml. Does it wait for the service to be healthy?**

**A:** `depends_on` only controls **startup order** – it starts `db` before `web`, but doesn't wait for `db` to be ready to accept connections. For true health-based waiting, use `depends_on` with `condition: service_healthy` and define a `healthcheck` for the dependent service. Otherwise, your app may try to connect before PostgreSQL is ready, causing connection errors.

**Q: What happens to data in a volume when you run `docker-compose down`?**

**A:** `docker-compose down` removes containers and networks but **preserves volumes** by default. Data persists. To remove volumes, use `docker-compose down -v`. This is important for production – you don't want to accidentally delete database data.

### **Practical / Troubleshooting**

**Q: Your web container can't connect to the database. How do you debug?**

**A:** Systematic debugging approach:
1. **Check containers are running**: `docker-compose ps` – both services should be "Up"
2. **Check they're on the same network**: `docker network inspect <network-name>` – verify both containers are listed
3. **Test DNS resolution**: `docker-compose exec web ping db` – if this fails, networking issue
4. **Check database is accepting connections**: `docker-compose exec db pg_isready -U appuser`
5. **Check connection string**: Verify environment variables (host should be service name `db`, not `localhost`)
6. **Check logs**: `docker-compose logs db` for database errors, `docker-compose logs web` for connection errors
7. **Test from web container**: `docker-compose exec web python -c "import psycopg2; conn = psycopg2.connect(host='db', ...)"`

**Q: How do you handle database migrations in a containerized environment?**

**A:** Common patterns:
- **Init scripts**: Place SQL scripts in `/docker-entrypoint-initdb.d/` (PostgreSQL runs these on first initialization)
- **Migration tool in app**: Run migrations as part of app startup (e.g., Flask-Migrate, Alembic)
- **Separate migration container**: Run migrations as a one-off job (`docker-compose run --rm migrations`)
- **CI/CD pipeline**: Run migrations before deploying new app version

For interviews, mention you'd use idempotent migrations, test in staging first, and have rollback procedures.

**Q: How would you scale a stateless web service in docker-compose?**

**A:** Use `docker-compose up -d --scale web=3`. This creates 3 instances of the `web` service. However, you need a **load balancer** (like nginx) in front, or use Docker Swarm mode, or Kubernetes. Plain docker-compose scaling doesn't provide load balancing – all instances listen on the same ports, which can conflict unless you use a reverse proxy.

**Q: Your docker-compose build is slow. How do you optimize it?**

**A:**
- **Layer caching**: Order Dockerfile instructions so frequently changing code is copied last
- **Use BuildKit**: `DOCKER_BUILDKIT=1 docker-compose build`
- **Cache mounts**: Use `RUN --mount=type=cache` for package managers (pip, npm)
- **Multi-stage builds**: Separate build and runtime stages
- **Parallel builds**: Build multiple services in parallel if they don't depend on each other
- **Use `.dockerignore`**: Exclude unnecessary files from build context

### **Behavior / Experience-Based**

**Q: Tell me about a time you debugged a networking issue between containers.**

**A:** (Example answer structure)
"I was deploying a microservice that needed to connect to Redis. The app worked locally but failed in Docker. I checked:
1. Containers were on the same network (`docker network inspect`)
2. DNS resolution (`ping redis` from app container)
3. Redis was listening (`docker-compose exec redis redis-cli ping`)
4. Found the issue: The app was using `localhost` instead of the service name `redis`. Fixed the connection string to use the service name, and it worked. This taught me to always use service names in docker-compose, never `localhost`."

**Q: How do you handle secrets (passwords, API keys) in docker-compose for production?**

**A:** Never hardcode secrets in `docker-compose.yml`. Options:
- **Docker secrets** (Swarm mode): Encrypted at rest, mounted as files
- **External secret managers**: HashiCorp Vault, AWS Secrets Manager – fetch at runtime
- **Environment files**: `.env` files (but secure them, don't commit)
- **CI/CD injection**: Inject secrets as environment variables in CI/CD pipeline
- **Secrets as volumes**: Mount secrets from host (with proper permissions)

For production, I'd use a secrets manager and rotate credentials regularly.

---

## 12. Real-World Challenges & Talking Points (Phase 3)

### **"Database connection refused" on startup**

**Challenge**: Web container starts before database is ready, causing connection errors.

**Solution**: Use healthchecks and `depends_on` with `condition: service_healthy`, or implement retry logic in your app (exponential backoff). In production, use init containers or readiness probes.

**How to talk about it**: "I learned to never assume dependencies are ready. I implemented healthchecks and proper dependency ordering. For critical services, I added retry logic with exponential backoff in the application code."

### **Port conflicts in docker-compose**

**Challenge**: Multiple services trying to bind to the same host port.

**Solution**: Only expose ports that need external access. Database shouldn't expose `5432` to host unless debugging. Use internal networking. If you need multiple instances, use a reverse proxy (nginx) that listens on one port and routes to backend services.

**How to talk about it**: "I follow the principle of least exposure – only expose what's necessary. Databases stay internal. I use nginx as a reverse proxy for multiple web instances, which also gives me SSL termination and load balancing."

### **Volume permissions issues**

**Challenge**: Database container runs as `postgres` user, but volume is owned by root, causing permission errors.

**Solution**: Use named volumes (Docker handles permissions better), or set proper ownership in entrypoint script. For bind mounts, ensure host directory has correct permissions.

**How to talk about it**: "I encountered this when switching from named volumes to bind mounts for development. I learned to check user IDs and use entrypoint scripts to fix permissions, or stick to named volumes for production."

### **docker-compose.yml becomes unmaintainable**

**Challenge**: As services grow, the YAML file becomes huge and hard to manage.

**Solution**: 
- Split into multiple compose files (`docker-compose.base.yml`, `docker-compose.override.yml`)
- Use `extends` or `include` (newer Compose spec)
- Use environment variable substitution
- Consider moving to Kubernetes or Docker Swarm for complex orchestration

**How to talk about it**: "I've seen docker-compose files grow to 500+ lines. I refactored by splitting into base and override files, using variables, and eventually migrated to Kubernetes for better orchestration capabilities. Docker Compose is great for local dev and small apps, but has limits."

### **Data persistence across deployments**

**Challenge**: Need to ensure database data survives container updates and restarts.

**Solution**: Use named volumes, document backup procedures, test restore process regularly. For production, use managed database services or dedicated database servers with proper backup strategies.

**How to talk about it**: "I always use named volumes for stateful services and document backup/restore procedures. I've set up automated backups that run daily and test restores monthly. For production, I prefer managed databases (RDS, Cloud SQL) for built-in backups and high availability."

---

## 13. When You're Comfortable

You are ready to move on when you can:
- Write a `docker-compose.yml` from scratch for a multi-service app.
- Explain how containers communicate via Docker networks and DNS.
- Debug networking issues between containers.
- Understand volumes and data persistence.
- Handle environment variables and secrets appropriately.

Next, we'll do **Phase 4 – Data & State Management** (advanced volume patterns, backups, migrations, and stateful workloads).


