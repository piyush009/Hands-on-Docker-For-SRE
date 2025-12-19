## Phase 5 – Observability, Health, and Debugging

**Goal**: Master Docker healthchecks, logging strategies, metrics collection, and debugging techniques. These are critical SRE skills for production containerized applications.

We'll enhance our Flask app with structured logging, metrics endpoints, and proper healthchecks, then practice debugging common issues.

---

## 1. Prerequisites

- Completed Phases 1-4.
- Understanding of basic monitoring concepts.

---

## 2. Project Structure

```
phase-05-observability-debugging/
├── app.py              # Flask app with logging, metrics, healthchecks
├── requirements.txt    # Dependencies (includes prometheus_client)
├── Dockerfile          # Dockerfile with healthcheck
├── docker-compose.yml  # Multi-service setup with logging
└── README.md           # This file
```

---

## 3. Observability Pillars

### 3.1. Logging

**Structured Logging**: Logs should be structured (JSON) for easy parsing and aggregation.

**Log Levels**:
- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages (non-critical issues)
- `ERROR`: Error messages (operations failed)
- `CRITICAL`: Critical errors (system may be unusable)

**Docker Logging**:
- Docker captures stdout/stderr from containers
- Use log drivers for production (json-file, syslog, gelf, etc.)
- Configure log rotation to prevent disk fill

### 3.2. Metrics

**Key Metrics to Track**:
- **Request rate**: Requests per second
- **Latency**: Response time (p50, p95, p99)
- **Error rate**: Percentage of failed requests
- **Resource usage**: CPU, memory, disk I/O
- **Business metrics**: Custom application metrics

**Metrics Formats**:
- Prometheus format (most common)
- StatsD
- Custom JSON endpoints

### 3.3. Healthchecks

**Types**:
- **Liveness**: Is the container alive? (restart if unhealthy)
- **Readiness**: Is the container ready to serve traffic? (don't route traffic if not ready)
- **Startup**: Is the container starting up? (give time before marking unhealthy)

**Docker Healthcheck**:
- Defined in Dockerfile or docker-compose.yml
- Runs periodically inside container
- Returns 0 (healthy) or 1 (unhealthy)

---

## 4. Enhanced Application

Our Flask app (`app.py`) includes:
- **Structured logging** with JSON format
- **Metrics endpoint** (`/metrics`) in Prometheus format
- **Health endpoints**: `/healthz` (liveness), `/readyz` (readiness)
- **Request logging middleware** to track all requests
- **Error handling** with proper logging

---

## 5. Hands-On: Build and Run

### 5.1. Start the Application

```bash
cd phase-05-observability-debugging
docker-compose up --build
```

### 5.2. Test Health Endpoints

```bash
# Liveness probe
curl http://localhost:8083/healthz

# Readiness probe
curl http://localhost:8083/readyz

# Metrics endpoint
curl http://localhost:8083/metrics
```

### 5.3. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100 web

# Since specific time
docker-compose logs --since 5m web
```

### 5.4. Check Container Health Status

```bash
# View health status
docker ps
# Look for STATUS column: "Up X minutes (healthy)" or "(unhealthy)"

# Inspect healthcheck details
docker inspect phase5-web | grep -A 10 Health
```

### 5.5. Generate Some Traffic

```bash
# Make requests to generate logs and metrics
for i in {1..10}; do curl http://localhost:8083/; sleep 1; done

# Check metrics
curl http://localhost:8083/metrics | grep http_requests_total
```

---

## 6. Logging Deep Dive

### 6.1. Docker Log Drivers

Docker supports multiple log drivers. Configure in `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Common Log Drivers**:
- `json-file`: Default, logs to JSON files
- `syslog`: Send to syslog daemon
- `gelf`: Send to Graylog
- `fluentd`: Send to Fluentd
- `awslogs`: Send to CloudWatch Logs

### 6.2. Structured Logging Example

Our app logs in JSON format:
```json
{"timestamp": "2024-01-15T10:30:45", "level": "INFO", "message": "Request processed", "method": "GET", "path": "/", "status": 200, "duration_ms": 12}
```

This makes it easy to:
- Parse logs with tools (jq, logstash, etc.)
- Filter by fields
- Aggregate metrics from logs

### 6.3. Log Aggregation Patterns

**For Production**:
- Use centralized logging (ELK stack, Loki, CloudWatch)
- Ship logs via log shippers (Fluentd, Filebeat)
- Set up log retention policies
- Monitor log volume and errors

---

## 7. Metrics Collection

### 7.1. Prometheus Metrics Format

Our `/metrics` endpoint exposes:
- `http_requests_total`: Counter of total requests
- `http_request_duration_seconds`: Histogram of request duration
- `http_errors_total`: Counter of errors

### 7.2. Scraping Metrics

**Prometheus Configuration** (example):
```yaml
scrape_configs:
  - job_name: 'phase5-web'
    static_configs:
      - targets: ['web:5000']
```

**Manual Scraping**:
```bash
curl http://localhost:8083/metrics
```

### 7.3. Key Metrics to Monitor

- **Request rate**: `rate(http_requests_total[5m])`
- **Error rate**: `rate(http_errors_total[5m]) / rate(http_requests_total[5m])`
- **Latency (p95)**: `histogram_quantile(0.95, http_request_duration_seconds_bucket)`
- **Container health**: Docker healthcheck status

---

## 8. Healthcheck Configuration

### 8.1. Dockerfile Healthcheck

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"
```

**Parameters**:
- `--interval`: Time between checks (default: 30s)
- `--timeout`: Time to wait for check (default: 30s)
- `--start-period`: Grace period before marking unhealthy (default: 0s)
- `--retries`: Consecutive failures before unhealthy (default: 3)
- `CMD`: Command to run (must return 0 or 1)

### 8.2. docker-compose Healthcheck

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 8.3. Liveness vs Readiness

**Liveness** (`/healthz`):
- Checks if app is alive
- If fails, Docker restarts container
- Should be lightweight (don't check dependencies)

**Readiness** (`/readyz`):
- Checks if app is ready to serve traffic
- Can check dependencies (database, cache)
- Used by orchestrators (K8s) to route traffic
- If fails, stop sending traffic but don't restart

---

## 9. Debugging Techniques

### 9.1. Container Inspection

```bash
# Inspect container configuration
docker inspect phase5-web

# View container logs
docker logs phase5-web

# Follow logs in real-time
docker logs -f phase5-web

# Exec into running container
docker exec -it phase5-web /bin/sh

# Check running processes
docker exec phase5-web ps aux

# Check network connections
docker exec phase5-web netstat -tuln
```

### 9.2. Resource Monitoring

```bash
# Container stats (CPU, memory, I/O)
docker stats phase5-web

# All containers
docker stats

# One-time stats
docker stats --no-stream phase5-web
```

### 9.3. Debugging Failed Containers

```bash
# View logs of stopped container
docker logs phase5-web

# Inspect exit code
docker inspect phase5-web | grep ExitCode

# Run container interactively to debug
docker run -it --rm phase5-flask:latest /bin/sh
```

### 9.4. Network Debugging

```bash
# Test connectivity from container
docker exec phase5-web ping -c 3 db

# Test HTTP endpoint
docker exec phase5-web curl http://localhost:5000/healthz

# Inspect network
docker network inspect phase-05-observability-debugging_default
```

### 9.5. Debugging Healthcheck Failures

```bash
# Manually run healthcheck command
docker exec phase5-web python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"

# Check healthcheck history
docker inspect phase5-web | grep -A 20 Health

# View healthcheck logs (if healthcheck writes to stdout)
docker logs phase5-web 2>&1 | grep -i health
```

---

## 10. Common Debugging Scenarios

### 10.1. Container Exits Immediately

**Symptoms**: Container starts and stops immediately.

**Debugging**:
```bash
# Check exit code
docker inspect phase5-web | grep ExitCode

# View logs
docker logs phase5-web

# Run interactively to see error
docker run -it --rm phase5-flask:latest
```

**Common Causes**:
- Application crashes on startup
- Missing environment variables
- Port already in use
- Permission errors

### 10.2. Healthcheck Always Failing

**Symptoms**: Container shows `(unhealthy)` status.

**Debugging**:
```bash
# Manually test healthcheck
docker exec phase5-web python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"

# Check if app is actually running
docker exec phase5-web ps aux | grep python

# Check if port is listening
docker exec phase5-web netstat -tuln | grep 5000

# View application logs
docker logs phase5-web
```

**Common Causes**:
- Healthcheck endpoint not responding
- Wrong port in healthcheck
- App not binding to 0.0.0.0
- Healthcheck timeout too short

### 10.3. High Memory Usage

**Symptoms**: Container using excessive memory.

**Debugging**:
```bash
# Monitor memory
docker stats phase5-web

# Check memory inside container
docker exec phase5-web free -h

# Check process memory
docker exec phase5-web ps aux --sort=-%mem
```

**Solutions**:
- Set memory limits: `docker run -m 512m ...`
- Investigate memory leaks in application
- Optimize application code
- Use memory profiling tools

### 10.4. Slow Response Times

**Symptoms**: High latency, slow requests.

**Debugging**:
```bash
# Check metrics
curl http://localhost:8083/metrics | grep duration

# Monitor resource usage
docker stats phase5-web

# Check database connectivity
docker exec phase5-web python -c "import psycopg2; conn = psycopg2.connect(...)"

# View application logs for slow queries
docker logs phase5-web | grep -i slow
```

**Common Causes**:
- Database connection issues
- High CPU usage
- Network latency
- Inefficient queries
- Resource limits too low

---

## 11. Interview POV – Questions from This Phase

### **Conceptual**

**Q: What is the difference between liveness and readiness probes?**

**A:**
- **Liveness probe**: Answers "Is the container alive?" If it fails, the orchestrator (Docker/K8s) restarts the container. Should be lightweight and not check external dependencies. Example: Can the app process respond to a simple HTTP request?

- **Readiness probe**: Answers "Is the container ready to serve traffic?" If it fails, the orchestrator stops routing traffic to the container but doesn't restart it. Can check dependencies (database, cache, etc.). Example: Can the app connect to the database and serve requests?

**Why it matters**: A container might be alive but not ready (e.g., still initializing, database not available). Restarting won't help if the issue is external. Readiness prevents routing traffic to containers that can't handle it.

**Q: How do you configure log rotation in Docker?**

**A:** Configure log driver options in `docker-compose.yml` or `docker run`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"      # Max size of log file before rotation
    max-file: "3"        # Number of log files to keep
```

Or via command line:
```bash
docker run --log-opt max-size=10m --log-opt max-file=3 ...
```

**Why it matters**: Without rotation, logs can fill disk space and crash the host. In production, I'd also use centralized logging (ELK, Loki) and ship logs off the host.

**Q: Explain Docker healthcheck parameters: interval, timeout, start-period, and retries.**

**A:**
- **`interval`**: Time between healthcheck executions (e.g., `30s`). How often Docker checks if container is healthy.

- **`timeout`**: Maximum time to wait for healthcheck command to complete (e.g., `10s`). If command takes longer, it's considered a failure.

- **`start-period`**: Grace period after container starts before marking unhealthy (e.g., `40s`). Useful for apps that take time to initialize. Failures during this period don't count.

- **`retries`**: Number of consecutive failures before marking unhealthy (e.g., `3`). Prevents transient failures from marking container unhealthy.

**Example**: `interval=30s, timeout=10s, start-period=40s, retries=3` means: Check every 30s, wait max 10s for response, give 40s grace period on startup, mark unhealthy after 3 consecutive failures.

**Q: What metrics should you monitor for a containerized web application?**

**A:** Key metrics to monitor:

**Application Metrics**:
- Request rate (requests/second)
- Error rate (errors/total requests)
- Latency (p50, p95, p99 percentiles)
- Response codes (2xx, 4xx, 5xx breakdown)

**Infrastructure Metrics**:
- CPU usage (per container)
- Memory usage (current and limit)
- Disk I/O (read/write operations)
- Network I/O (bytes sent/received)

**Docker-Specific**:
- Container health status (healthy/unhealthy)
- Container restart count
- Container uptime

**Business Metrics** (application-specific):
- Active users, transactions per second, etc.

**Tools**: Prometheus + Grafana, Datadog, CloudWatch, etc. I'd set up alerts on error rate > 1%, latency p95 > 500ms, memory usage > 80%, and container restarts.

**Q: How do you debug a container that keeps restarting?**

**A:** Systematic debugging approach:

1. **Check exit code**: `docker inspect <container> | grep ExitCode` – non-zero means container exited with error.

2. **View logs**: `docker logs <container>` – look for error messages, stack traces, or application logs explaining why it exited.

3. **Check restart policy**: `docker inspect <container> | grep RestartPolicy` – might be restarting due to policy.

4. **Run interactively**: `docker run -it --rm <image>` – run container interactively to see startup errors in real-time.

5. **Check dependencies**: If app depends on database/cache, verify those are available and healthy.

6. **Check resource limits**: `docker stats` – might be OOM killed if memory limit too low.

7. **Check healthcheck**: If healthcheck fails repeatedly, container might be marked unhealthy and restarted.

**Common causes**: Missing environment variables, port conflicts, database connection failures, application crashes, OOM kills, healthcheck failures.

**Q: What is structured logging and why is it important?**

**A:** **Structured logging** means logs are formatted in a machine-parseable format (usually JSON) with consistent fields, rather than free-form text.

**Example structured log**:
```json
{"timestamp": "2024-01-15T10:30:45Z", "level": "ERROR", "service": "web", "method": "GET", "path": "/api/users", "status": 500, "duration_ms": 120, "error": "Database connection failed"}
```

**Benefits**:
- **Easy parsing**: Tools can extract fields automatically
- **Filtering**: Filter by level, service, status code, etc.
- **Aggregation**: Count errors by service, calculate average latency, etc.
- **Searchability**: Find all errors for specific endpoint quickly
- **Integration**: Works well with log aggregation tools (ELK, Loki, Splunk)

**In production**: I'd use structured logging (JSON) and ship logs to a centralized system. This enables real-time alerting, dashboards, and troubleshooting.

### **Practical / Troubleshooting**

**Q: Your container shows as unhealthy, but the application works when you curl it manually. What could be wrong?**

**A:** Common causes:

1. **Healthcheck endpoint mismatch**: Healthcheck might be hitting wrong endpoint or port. Verify healthcheck command matches actual endpoint.

2. **Network binding**: App might bind to `127.0.0.1` instead of `0.0.0.0`. Healthcheck runs inside container, needs `0.0.0.0`.

3. **Timeout too short**: Healthcheck timeout might be shorter than app response time. Increase `--timeout`.

4. **Start period**: App might still be initializing. Check if `start-period` is sufficient.

5. **Healthcheck command error**: Healthcheck command itself might be failing (missing tool, wrong path). Test command manually: `docker exec <container> <healthcheck-command>`.

**Debugging steps**:
- Manually run healthcheck command inside container
- Check if endpoint responds: `docker exec <container> curl http://localhost:5000/healthz`
- Verify app is listening: `docker exec <container> netstat -tuln`
- Check healthcheck configuration: `docker inspect <container> | grep -A 10 Health`

**Q: How do you handle log aggregation for hundreds of containers?**

**A:** Use centralized logging architecture:

1. **Log Shippers**: Deploy log shippers (Fluentd, Filebeat, Logstash) as sidecar containers or daemonsets that collect logs from containers and ship to central system.

2. **Log Drivers**: Configure Docker log drivers (syslog, gelf, fluentd) to send logs directly to aggregation system.

3. **Centralized System**: Use ELK stack (Elasticsearch, Logstash, Kibana), Loki + Grafana, Splunk, or cloud services (CloudWatch, Datadog).

4. **Log Retention**: Set retention policies (e.g., 30 days hot, 90 days cold storage) to manage costs.

5. **Indexing**: Index logs by service, environment, timestamp for fast searching.

6. **Monitoring**: Monitor log volume, ingestion rate, and storage usage.

**Example**: I'd use Fluentd as daemonset to collect logs, ship to Elasticsearch, and visualize in Kibana. Set up alerts for error spikes and log ingestion failures.

**Q: Your application is slow, but CPU and memory look fine. How do you debug?**

**A:** Investigate beyond CPU/memory:

1. **Check latency metrics**: Look at p95/p99 latency from metrics endpoint. Identify slow endpoints.

2. **Database performance**: Check database connection pool, query performance, slow query logs. Database might be bottleneck.

3. **Network latency**: Check network I/O, DNS resolution time, connection timeouts. Use `docker exec <container> ping <dependency>`.

4. **I/O wait**: Check disk I/O stats (`docker stats` shows I/O). High I/O wait can slow app even if CPU is low.

5. **Application logs**: Look for slow queries, retries, timeouts in logs. Check for blocking operations.

6. **Dependencies**: Check external dependencies (APIs, databases, caches). They might be slow.

7. **Concurrency**: Check if app is single-threaded and blocking on I/O. Might need more workers/threads.

**Tools**: APM tools (New Relic, Datadog APM), database query analyzers, network tracing.

**Q: How do you set up alerting for containerized applications?**

**A:** Multi-layer alerting strategy:

1. **Infrastructure Alerts**: 
   - Container down (healthcheck failures, restarts)
   - High CPU/memory usage
   - Disk space low
   - Network errors

2. **Application Alerts**:
   - Error rate > threshold (e.g., > 1%)
   - Latency p95 > threshold (e.g., > 500ms)
   - Request rate anomalies
   - Healthcheck failures

3. **Business Alerts**:
   - Transaction failures
   - SLA violations
   - Custom business metrics

**Implementation**:
- Use monitoring tools (Prometheus + Alertmanager, Datadog, CloudWatch)
- Define alert rules (e.g., `error_rate > 0.01 for 5 minutes`)
- Set up notification channels (PagerDuty, Slack, email)
- Use alerting best practices: avoid alert fatigue, set appropriate thresholds, use runbooks

**Example**: I'd set up Prometheus to scrape metrics, define alert rules, and use Alertmanager to route to PagerDuty for critical alerts and Slack for warnings.

### **Behavior / Experience-Based**

**Q: Tell me about a time you debugged a production issue using container logs.**

**A:** (Example answer structure)

"I was on-call when users reported 500 errors. I checked container logs using `docker logs` and saw database connection timeouts. The logs showed connection pool exhaustion – too many connections to database.

I investigated:
1. Checked database connection pool settings in app config
2. Verified database was healthy (`docker exec db pg_isready`)
3. Found the root cause: A recent deployment increased connection pool size but database max_connections wasn't increased

I fixed by:
1. Reducing connection pool size in app config
2. Adding connection pool monitoring/metrics
3. Setting up alerting for connection pool usage

This taught me to always check resource limits (connections, memory, CPU) when debugging and to monitor connection pool metrics."

**Q: How do you ensure observability in a microservices architecture with Docker?**

**A:** Comprehensive observability strategy:

1. **Distributed Tracing**: Use tools (Jaeger, Zipkin) to trace requests across services. Add trace IDs to logs for correlation.

2. **Centralized Logging**: All services log to central system (ELK, Loki) with consistent format. Include service name, trace ID, request ID in logs.

3. **Metrics**: Each service exposes Prometheus metrics. Use service mesh (Istio) or sidecar for metrics collection.

4. **Healthchecks**: Every service has liveness and readiness probes. Orchestrator uses these for routing and restarts.

5. **Service Discovery**: Use service mesh or DNS for service discovery. Log service interactions.

6. **Correlation IDs**: Pass request/trace IDs through all services to correlate logs and traces.

7. **Dashboards**: Create dashboards per service and aggregate views. Show error rates, latency, throughput.

**Tools**: Prometheus + Grafana for metrics, ELK/Loki for logs, Jaeger for tracing, service mesh for observability.

---

## 12. Real-World Challenges & Talking Points (Phase 5)

### **"Noisy neighbor" containers**

**Challenge**: One container consuming excessive resources (CPU, memory, I/O) affects other containers on the same host.

**Solution**: Set resource limits (`-m`, `--cpus`) for all containers. Use resource quotas. Monitor resource usage and alert on high usage. In production, use orchestrators (K8s) with resource requests/limits and quality of service classes.

**How to talk about it**: "I've seen containers without limits consume all host resources. I always set memory and CPU limits. In Kubernetes, I use resource requests and limits, and monitor with Prometheus. For critical workloads, I use node selectors and taints/tolerations to isolate them."

### **Log volume explosion**

**Challenge**: High-volume logging fills disk space, crashes containers or host.

**Solution**: Configure log rotation (max-size, max-file). Use structured logging to reduce verbosity. Ship logs to centralized system and delete local logs. Set up disk space monitoring and alerts. Use log sampling for high-volume endpoints.

**How to talk about it**: "I've seen log volumes grow to hundreds of GB. I implemented log rotation, centralized logging, and log retention policies. I also reduced log verbosity by using appropriate log levels and structured logging. Set up alerts for disk usage > 80%."

### **Healthcheck false positives**

**Challenge**: Healthcheck fails intermittently due to transient issues (network blip, slow dependency), causing unnecessary restarts.

**Solution**: Increase `retries` to require multiple consecutive failures. Increase `timeout` if healthcheck is slow. Make healthcheck lightweight (don't check external dependencies for liveness). Use separate readiness probe for dependency checks. Implement retry logic in healthcheck command.

**How to talk about it**: "I've seen healthchecks fail due to transient database latency, causing restarts. I separated liveness (lightweight) from readiness (checks dependencies), increased retries, and added retry logic in healthcheck. This reduced false positives significantly."

### **Debugging in production without breaking things**

**Challenge**: Need to debug production issues but can't risk breaking running containers.

**Solution**: 
- Use read-only debugging: `docker exec` to inspect, don't modify
- Create debugging containers on same network: `docker run --rm -it --network <network> <image>`
- Use sidecar containers for debugging tools
- Enable debug logging only when needed (via environment variable)
- Use APM tools for non-invasive debugging
- Test debugging commands in staging first

**How to talk about it**: "I always use read-only operations (`docker exec`, `docker logs`) for production debugging. I create temporary debugging containers on the same network rather than modifying running containers. I also use APM tools for non-invasive debugging and test all debugging procedures in staging first."

### **Metrics cardinality explosion**

**Challenge**: Too many unique metric labels (e.g., per-user metrics) causes Prometheus storage and query performance issues.

**Solution**: Limit label cardinality. Use aggregation instead of per-entity metrics. Sample high-cardinality metrics. Use recording rules to pre-aggregate. Monitor metric cardinality and alert on high cardinality.

**How to talk about it**: "I've seen metrics with user_id labels create millions of time series. I switched to aggregated metrics (e.g., by endpoint, status code) and used sampling for high-cardinality data. I monitor metric cardinality and set limits. For user-specific metrics, I use application-level analytics instead of Prometheus."

---

## 13. When You're Comfortable

You are ready to move on when you can:
- Configure and debug Docker healthchecks effectively.
- Understand liveness vs readiness probes and when to use each.
- Set up structured logging and log aggregation.
- Expose and scrape Prometheus metrics.
- Debug container issues systematically (logs, stats, exec, network).
- Explain observability strategy for microservices.

Next, we'll do **Phase 6 – Security, Supply Chain, and Policies** (image scanning, least-privilege, resource limits, and security best practices).

