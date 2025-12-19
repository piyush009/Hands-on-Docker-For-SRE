## Phase 8 – Advanced Docker Interview Questions for SRE & Senior SRE

**Goal**: Master advanced Docker concepts and be prepared for challenging SRE/Senior SRE interview questions. This phase consolidates knowledge from Phases 1-7 and adds advanced Docker topics.

**Focus**: Docker-only (no Kubernetes). Deep dive into Docker internals, advanced networking, storage, performance, and production scenarios.

---

## Table of Contents

1. [Docker Internals & Architecture](#1-docker-internals--architecture)
2. [Advanced Networking](#2-advanced-networking)
3. [Storage & Filesystems](#3-storage--filesystems)
4. [Performance & Optimization](#4-performance--optimization)
5. [Security & Isolation](#5-security--isolation)
6. [Production Architecture](#6-production-architecture)
7. [Troubleshooting & Debugging](#7-troubleshooting--debugging)
8. [Docker Swarm](#8-docker-swarm)
9. [CI/CD & Operations](#9-cicd--operations)
10. [Scenario-Based Questions](#10-scenario-based-questions)

---

## 1. Docker Internals & Architecture

### Q1: Explain the Docker architecture. What are containerd, runc, and the Docker daemon? How do they interact?

**A:** Docker uses a **client-server architecture** with multiple components:

**Components**:

1. **Docker Client** (`docker` CLI):
   - User-facing command-line interface
   - Sends commands to Docker daemon via API

2. **Docker Daemon** (`dockerd`):
   - Background service managing containers, images, networks, volumes
   - Exposes REST API (Docker Engine API)
   - Orchestrates container lifecycle

3. **containerd**:
   - Industry-standard container runtime
   - Manages container lifecycle (create, start, stop, delete)
   - Handles image management (pull, push, store)
   - Manages low-level operations (snapshots, metadata)

4. **runc**:
   - OCI-compliant container runtime
   - Actually creates and runs containers
   - Implements OCI runtime specification
   - Uses Linux namespaces and cgroups

**Interaction Flow**:
```
User → docker CLI → Docker Daemon → containerd → runc → Container
```

**Example**: When you run `docker run nginx`:
1. Docker CLI sends request to Docker daemon
2. Docker daemon checks if image exists, pulls if needed
3. Docker daemon asks containerd to create container
4. containerd prepares container filesystem (snapshots)
5. containerd calls runc to create container process
6. runc creates namespaces, cgroups, and starts container

**Why this architecture**:
- **Separation of concerns**: Each component has specific responsibility
- **Modularity**: Can swap runtimes (containerd can use different runtimes)
- **Industry standard**: containerd and runc are OCI-compliant, used by Kubernetes too
- **Maintainability**: Easier to maintain and update components independently

**For SRE**: Understanding this helps debug issues at the right layer. If container won't start, check runc logs. If image pull fails, check containerd. If API calls fail, check Docker daemon.

---

### Q2: What are Linux namespaces and cgroups? How does Docker use them?

**A:** **Linux namespaces** and **cgroups** are kernel features that Docker uses for container isolation.

**Linux Namespaces** (Isolation):

Namespaces provide isolation by giving processes their own view of system resources:

1. **PID namespace**: Isolated process tree (container sees only its processes)
2. **Network namespace**: Isolated network stack (own IP, routing table, ports)
3. **Mount namespace**: Isolated filesystem mount points
4. **UTS namespace**: Isolated hostname and domain name
5. **IPC namespace**: Isolated inter-process communication (shared memory, semaphores)
6. **User namespace**: Isolated user/group IDs (root in container ≠ root on host)

**cgroups** (Control Groups - Resource Limits):

cgroups limit and account for resource usage:

1. **CPU**: Limit CPU usage (shares, quotas, sets)
2. **Memory**: Limit memory usage (hard limit, soft limit)
3. **I/O**: Limit disk I/O (read/write bandwidth)
4. **Devices**: Control access to devices
5. **Network**: Limit network bandwidth (with net_cls cgroup)

**How Docker Uses Them**:

**Namespaces**:
- Each container gets its own set of namespaces
- Processes in container can't see host processes (PID namespace)
- Container has its own network interface (Network namespace)
- Container has isolated filesystem (Mount namespace)

**cgroups**:
- Docker sets cgroup limits via `docker run -m 512m --cpus="1.0"`
- Memory limit: `memory.limit_in_bytes` cgroup
- CPU limit: `cpu.cfs_quota_us` and `cpu.cfs_period_us` cgroups
- I/O limits: `blkio` cgroup

**Example**:
```bash
# Container with resource limits
docker run -m 512m --cpus="1.0" nginx

# Docker creates:
# - Namespaces: PID, Network, Mount, UTS, IPC, User
# - cgroups: /sys/fs/cgroup/memory/docker/<container-id>/
#            /sys/fs/cgroup/cpu/docker/<container-id>/
```

**For SRE**: Understanding namespaces helps debug "why can't container see X?" Understanding cgroups helps debug "why is container slow?" or "why did container get OOM killed?"

**Advanced**: Docker also uses **seccomp** (syscall filtering) and **AppArmor/SELinux** (MAC) for additional security.

---

### Q3: Explain Docker's storage drivers. What is overlay2? How does it work?

**A:** **Storage drivers** determine how Docker manages image layers and container filesystems.

**Common Storage Drivers**:

1. **overlay2** (default, recommended):
   - Uses Linux overlay filesystem
   - Fast, efficient, native support
   - Supports up to 128 layers

2. **aufs** (legacy):
   - Older driver, not in mainline kernel
   - Being phased out

3. **devicemapper** (legacy):
   - Uses device mapper thin provisioning
   - More complex, less efficient

4. **btrfs/zfs**:
   - Uses btrfs/zfs snapshots
   - Requires filesystem support

**overlay2 How It Works**:

overlay2 uses **overlay filesystem** (Linux kernel feature) to combine multiple layers:

**Layers**:
- **Lower layers** (read-only): Image layers stacked bottom-up
- **Upper layer** (read-write): Container-specific changes
- **Merged**: Combined view (what container sees)

**Example**:
```
Image: nginx:latest
├── Layer 1 (base): /bin, /lib, /usr (read-only)
├── Layer 2 (nginx): /usr/sbin/nginx (read-only)
└── Container layer (upper): /var/log/nginx/access.log (read-write)

Merged view (what container sees):
├── /bin, /lib, /usr (from Layer 1)
├── /usr/sbin/nginx (from Layer 2)
└── /var/log/nginx/access.log (from container layer)
```

**Copy-on-Write (CoW)**:
- Reading: Reads from lower layers (if file exists) or upper layer
- Writing: Creates copy in upper layer (copy-on-write)
- Deleting: Creates "whiteout" file in upper layer

**Benefits**:
- **Space efficient**: Shared layers across containers
- **Fast**: No copying until write
- **Efficient**: Only changed files stored

**Storage Location**:
- `/var/lib/docker/overlay2/` (on Linux)
- Each layer has `diff/` (files), `link` (layer ID), `lower` (parent layers)

**For SRE**: 
- Check storage driver: `docker info | grep "Storage Driver"`
- Monitor disk usage: `docker system df`
- Clean up: `docker system prune`
- If disk full, check overlay2 directory size

**Performance**: overlay2 is fastest for most workloads. Use `--storage-driver` only if you have specific requirements.

---

### Q4: How does Docker handle multi-architecture images (ARM64, AMD64)? Explain buildx.

**A:** **Multi-architecture images** allow same image tag to work on different CPU architectures (ARM64, AMD64, ARMv7, etc.).

**Problem**: 
- Image built on AMD64 won't run on ARM64
- Need different images for different architectures
- Want single tag (`nginx:latest`) to work everywhere

**Solution**: **Docker Buildx** (extended build capabilities)

**Docker Buildx Features**:

1. **Multi-platform builds**: Build for multiple architectures simultaneously
2. **BuildKit backend**: Faster, more efficient builds
3. **Advanced caching**: Better cache management

**How Multi-Arch Works**:

**Manifest Lists** (Image Index):
- Special manifest pointing to architecture-specific manifests
- Docker automatically selects correct image for host architecture

**Example**:
```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t myapp:v1.0.0 \
  --push .

# Creates manifest list with 3 images:
# - linux/amd64 → sha256:abc...
# - linux/arm64 → sha256:def...
# - linux/arm/v7 → sha256:ghi...
```

**Buildx Setup**:
```bash
# Create buildx builder instance
docker buildx create --name multiarch --use

# Inspect builder
docker buildx inspect

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:v1.0.0 .
```

**QEMU Emulation**:
- Buildx uses QEMU to emulate other architectures
- Can build ARM64 image on AMD64 host (slower)
- Or use native builders (faster)

**For SRE**:
- **CI/CD**: Build multi-arch images in pipeline
- **Edge/IoT**: Deploy to ARM devices
- **Cloud**: Support multiple instance types
- **Performance**: Use native builders for speed

**Best Practices**:
- Build for target architectures in CI/CD
- Test on actual hardware when possible
- Use `--load` for local testing, `--push` for registry
- Cache base images per architecture

**Example CI/CD**:
```yaml
- name: Build multi-arch
  run: |
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t myapp:${{ github.sha }} \
      --push .
```

---

### Q5: What is the difference between Docker image layers and how does layer caching work?

**A:** **Docker images** are built from **layers** (read-only filesystem snapshots). Understanding layers is crucial for optimization.

**Image Layers**:

Each instruction in Dockerfile creates a layer:
```dockerfile
FROM python:3.11-slim        # Layer 1: Base image layers
RUN apt-get update           # Layer 2: Package list update
RUN apt-get install -y curl # Layer 3: Install curl
COPY app.py /app/            # Layer 4: Copy app.py
RUN pip install -r req.txt  # Layer 5: Install Python packages
```

**Layer Characteristics**:
- **Immutable**: Once created, can't be changed
- **Cached**: Docker caches layers for reuse
- **Shared**: Multiple images can share same layers
- **Ordered**: Layers stacked in order

**Layer Caching**:

Docker caches layers and reuses them if:
1. **Instruction unchanged**: Same instruction, same context
2. **Parent layers unchanged**: All previous layers match
3. **Build context unchanged**: Files used in instruction unchanged

**Cache Invalidation**:

Cache breaks (invalidates) when:
- Instruction changes
- Any parent layer changes
- Build context file changes (for COPY/ADD)

**Example**:
```dockerfile
# Build 1
FROM python:3.11-slim        # Cache: MISS (first time)
COPY requirements.txt .       # Cache: MISS
RUN pip install -r req.txt   # Cache: MISS

# Build 2 (requirements.txt changed)
FROM python:3.11-slim        # Cache: HIT (unchanged)
COPY requirements.txt .       # Cache: MISS (file changed)
RUN pip install -r req.txt   # Cache: MISS (parent changed)
```

**Optimization Strategy**:

**Order matters**:
```dockerfile
# BAD: Code changes invalidate dependency cache
COPY . .
RUN pip install -r requirements.txt

# GOOD: Dependencies cached separately
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

**Layer Size**:
- Each layer adds to image size
- Minimize layers (combine RUN commands)
- But balance with cache efficiency

**For SRE**:
- **CI/CD**: Optimize Dockerfile for cache hits
- **Build time**: Faster builds with good caching
- **Storage**: Shared layers save disk space
- **Debugging**: `docker history <image>` shows layers

**Advanced**:
- Use `--cache-from` in CI to share cache
- Use BuildKit cache mounts: `RUN --mount=type=cache`
- Multi-stage builds for smaller final images

---

## 2. Advanced Networking

### Q6: Explain Docker's network drivers. What's the difference between bridge, host, macvlan, and overlay networks?

**A:** Docker supports multiple **network drivers** for different use cases.

**Network Drivers**:

1. **bridge** (default):
   - **How**: Virtual network bridge on host
   - **Isolation**: Containers isolated from host network
   - **Use case**: Default for single-host containers
   - **Features**: Port mapping, DNS resolution between containers
   - **Limitation**: Single host only

2. **host**:
   - **How**: Container shares host's network stack directly
   - **Isolation**: No network isolation
   - **Use case**: High performance, need host network access
   - **Features**: No port mapping needed, direct host network
   - **Limitation**: Less secure, port conflicts

3. **macvlan**:
   - **How**: Assigns MAC address to container, appears as physical device
   - **Isolation**: Container gets IP on physical network
   - **Use case**: Containers need to be on physical network (legacy apps, network appliances)
   - **Features**: Direct network access, no NAT
   - **Limitation**: Requires network configuration, MAC address management

4. **overlay**:
   - **How**: Multi-host network using VXLAN
   - **Isolation**: Network spans multiple hosts
   - **Use case**: Docker Swarm, multi-host containers
   - **Features**: Cross-host communication, encryption
   - **Limitation**: More complex, requires Swarm or external KV store

5. **ipvlan**:
   - **How**: Similar to macvlan but shares MAC address
   - **Isolation**: Containers share MAC, different IPs
   - **Use case**: When MAC addresses are limited
   - **Features**: More efficient than macvlan
   - **Limitation**: Less common, driver support varies

**Comparison**:

| Driver | Isolation | Performance | Use Case |
|--------|-----------|-------------|----------|
| bridge | High | Good | Default, single host |
| host | None | Best | High performance, single host |
| macvlan | Medium | Excellent | Physical network integration |
| overlay | High | Good | Multi-host, Swarm |
| ipvlan | Medium | Excellent | MAC-limited networks |

**Example Use Cases**:

**bridge** (most common):
```bash
docker network create mybridge
docker run --network mybridge nginx
```

**host** (high performance):
```bash
docker run --network host nginx
# Container uses host IP directly
```

**macvlan** (physical network):
```bash
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  mymacvlan
docker run --network mymacvlan --ip=192.168.1.100 nginx
```

**overlay** (Swarm):
```bash
docker network create -d overlay myoverlay
# Works across Swarm nodes
```

**For SRE**:
- **bridge**: Default choice for most applications
- **host**: Use for performance-critical apps (monitoring, networking tools)
- **macvlan**: Legacy apps needing physical network
- **overlay**: Multi-host deployments (Swarm)
- **Security**: bridge > overlay > macvlan > host (isolation)

**Troubleshooting**:
- `docker network inspect <network>`: See network details
- `docker network ls`: List networks
- `iptables -t nat -L`: Check NAT rules (bridge network)

---

### Q7: How does Docker's DNS resolution work between containers? What is the embedded DNS server?

**A:** Docker provides **automatic DNS resolution** between containers on the same network.

**Embedded DNS Server**:

Docker runs a **built-in DNS server** (port 53) in each container that:
- Resolves container names to IP addresses
- Handles service discovery
- Falls back to host DNS for external names

**How It Works**:

1. **Container Name Resolution**:
   - Containers can reach each other by **name** (not just IP)
   - Docker maintains name-to-IP mapping
   - Updates automatically when containers start/stop

2. **Network Scope**:
   - DNS resolution works within same network
   - Containers on different networks can't resolve each other
   - Use network aliases for multiple names

**Example**:
```bash
# Create network
docker network create mynet

# Start containers
docker run -d --name web --network mynet nginx
docker run -d --name db --network mynet postgres

# From web container, can reach db by name
docker exec web ping db
# Resolves db → 172.18.0.3 (example)
```

**DNS Resolution Order**:

1. **Container name**: `db` → container IP
2. **Network alias**: `database` → container IP (if alias set)
3. **External DNS**: `google.com` → forwarded to host DNS

**Custom DNS**:

Override DNS servers:
```bash
docker run --dns=8.8.8.8 --dns=8.8.4.4 nginx
```

**Docker Compose DNS**:

In docker-compose, service names become DNS names:
```yaml
services:
  web:
    # Can reach db by name "db"
  db:
    # Can reach web by name "web"
```

**Network Aliases**:

Multiple names for same container:
```bash
docker run --name app \
  --network-alias api \
  --network-alias backend \
  myapp
# Resolvable as: app, api, backend
```

**For SRE**:
- **Service discovery**: Use container names, not IPs
- **Dynamic IPs**: Don't hardcode IPs, use names
- **Debugging**: `docker exec <container> nslookup <name>`
- **Issues**: If DNS fails, check network membership

**Troubleshooting**:
```bash
# Check DNS resolution
docker exec web nslookup db

# Check embedded DNS
docker exec web cat /etc/resolv.conf
# Should show: nameserver 127.0.0.11 (embedded DNS)

# Test connectivity
docker exec web ping db
```

**Advanced**:
- **External DNS**: Containers can resolve external domains
- **DNS search domains**: Configured via `--dns-search`
- **Hostname**: Set via `--hostname`, affects DNS

**Limitations**:
- DNS only works within same network
- Name resolution is network-scoped
- Circular dependencies can cause issues

---

### Q8: Explain Docker's port mapping and how it works at the network level.

**A:** **Port mapping** (`-p` flag) exposes container ports to host, enabling external access.

**How Port Mapping Works**:

Docker uses **iptables NAT rules** to forward traffic:

1. **Host listens**: Docker binds to host port
2. **NAT translation**: iptables forwards packets
3. **Container receives**: Traffic forwarded to container port

**Example**:
```bash
docker run -p 8080:80 nginx
# Host port 8080 → Container port 80
```

**Network Flow**:
```
External → Host:8080 → iptables NAT → Container:80
```

**iptables Rules**:

Docker creates NAT rules automatically:
```bash
# Check NAT rules
iptables -t nat -L DOCKER

# Example rule:
# DNAT tcp -- 0.0.0.0/0 0.0.0.0/0 tcp dpt:8080 to:172.17.0.2:80
```

**Port Mapping Modes**:

1. **Explicit mapping**: `-p 8080:80`
   - Host:8080 → Container:80

2. **Auto host port**: `-p 80`
   - Docker chooses random host port
   - Use `docker ps` to see mapping

3. **Bind to specific IP**: `-p 127.0.0.1:8080:80`
   - Only accessible from localhost

4. **UDP**: `-p 8080:80/udp`
   - UDP port mapping

**Port Range**:
```bash
docker run -p 8000-8010:8000-8010 myapp
# Maps port range
```

**Publish All Ports**:
```bash
docker run -P nginx
# Publishes all EXPOSE ports
```

**For SRE**:
- **Security**: Bind to specific IP for internal services
- **Port conflicts**: Check `netstat -tuln` before mapping
- **Firewall**: Ensure iptables/firewall allows traffic
- **Debugging**: `iptables -t nat -L -v` to see rules

**Common Issues**:

1. **Port already in use**:
   ```bash
   # Error: bind: address already in use
   # Solution: Use different port or stop conflicting service
   ```

2. **Can't access from outside**:
   - Check firewall rules
   - Check iptables NAT rules
   - Verify port mapping: `docker ps`

3. **Connection refused**:
   - Container not listening on port
   - Wrong port mapping
   - App binding to 127.0.0.1 instead of 0.0.0.0

**Advanced**:
- **Host network mode**: `--network host` bypasses port mapping
- **Custom networks**: Port mapping works with bridge networks
- **Swarm mode**: Different port publishing (ingress mode)

**Performance**:
- Port mapping adds small overhead (NAT)
- Use host network for high-performance apps
- Consider macvlan for direct network access

---

## 3. Storage & Filesystems

### Q9: How do Docker volumes work? Explain the difference between named volumes, anonymous volumes, and bind mounts.

**A:** **Volumes** are Docker's mechanism for persistent data storage.

**Volume Types**:

1. **Named Volumes** (Managed by Docker):
   ```bash
   docker volume create mydata
   docker run -v mydata:/data nginx
   ```
   - **Location**: `/var/lib/docker/volumes/<name>/_data`
   - **Managed**: Docker creates, manages, can list/remove
   - **Portable**: Works across platforms
   - **Use case**: Database data, application data

2. **Anonymous Volumes**:
   ```bash
   docker run -v /data nginx
   ```
   - **Location**: `/var/lib/docker/volumes/<random-id>/_data`
   - **Not named**: Random ID, harder to manage
   - **Use case**: Temporary data, don't need to reference

3. **Bind Mounts** (Host directory):
   ```bash
   docker run -v /host/path:/container/path nginx
   ```
   - **Location**: Direct host directory
   - **Not managed**: Docker doesn't manage these
   - **Portable**: No (tied to host paths)
   - **Use case**: Development, config files, logs

**Comparison**:

| Type | Managed | Portable | Use Case |
|------|---------|----------|----------|
| Named Volume | Yes | Yes | Production data |
| Anonymous Volume | Partial | Yes | Temporary data |
| Bind Mount | No | No | Development, configs |

**Volume Drivers**:

Docker supports **volume drivers** for different storage backends:
- **local** (default): Host filesystem
- **nfs**: NFS mount
- **cifs**: SMB/CIFS share
- **cloud**: AWS EBS, Azure Disk, etc.

**Example NFS Volume**:
```bash
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100 \
  --opt device=:/exports \
  nfs-volume
```

**Volume Lifecycle**:

**Create**:
```bash
docker volume create myvol
```

**Inspect**:
```bash
docker volume inspect myvol
```

**List**:
```bash
docker volume ls
```

**Remove**:
```bash
docker volume rm myvol
# Or: docker volume prune (remove unused)
```

**Volume in Docker Compose**:
```yaml
volumes:
  db_data:
    driver: local

services:
  db:
    volumes:
      - db_data:/var/lib/postgresql/data
```

**For SRE**:
- **Production**: Use named volumes for data persistence
- **Backup**: Backup `/var/lib/docker/volumes/` or use volume plugins
- **Migration**: Copy volume data between hosts
- **Performance**: Named volumes often faster than bind mounts

**Backup Strategy**:
```bash
# Backup volume
docker run --rm -v myvol:/data -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz /data

# Restore
docker run --rm -v myvol:/data -v $(pwd):/backup \
  alpine tar xzf /backup/backup.tar.gz -C /
```

**Advanced**:
- **Volume plugins**: Extend Docker with custom storage
- **tmpfs mounts**: In-memory storage (`--tmpfs`)
- **Read-only volumes**: `-v myvol:/data:ro`

---

### Q10: Explain copy-on-write (CoW) in Docker. How does it affect performance?

**A:** **Copy-on-Write (CoW)** is Docker's mechanism for efficient storage and layer management.

**What is CoW**:

- **Principle**: Don't copy data until it's modified
- **Efficiency**: Share data between containers/images until write
- **Implementation**: Used by storage drivers (overlay2, devicemapper)

**How CoW Works**:

**Image Layers** (Read-only):
- Base image layers shared across containers
- Multiple containers can read same layer
- No copying needed for reads

**Container Layer** (Read-write):
- Each container has thin writable layer
- Writes create copies in container layer
- Original layer unchanged

**Example**:
```
Base Image: nginx:latest
├── Layer 1: /usr/bin (read-only)
├── Layer 2: /etc/nginx (read-only)
└── Container A writes to /etc/nginx/nginx.conf
    → Copy created in Container A's writable layer
    → Container B still reads from Layer 2
```

**CoW Operations**:

1. **Read**:
   - Check container layer first
   - If not found, read from image layers
   - No copying needed

2. **Write**:
   - If file in image layer: Copy to container layer (copy-on-write)
   - If file in container layer: Modify directly
   - Original unchanged

3. **Delete**:
   - Create "whiteout" file in container layer
   - Hides file from image layers

**Performance Implications**:

**Benefits**:
- **Space efficient**: Shared layers save disk space
- **Fast reads**: No copying for reads
- **Fast container creation**: Thin writable layer

**Overhead**:
- **First write**: Copy operation (slower)
- **Many small files**: Can be slow (many copies)
- **Large files**: Copy can be expensive

**Performance Tips**:

1. **Minimize writes to image layers**:
   ```dockerfile
   # BAD: Many writes
   RUN touch file1 && touch file2 && touch file3
   
   # GOOD: Single layer
   RUN touch file1 file2 file3
   ```

2. **Use volumes for frequently written data**:
   ```bash
   # Logs, databases → volumes (bypass CoW)
   docker run -v /var/log nginx
   ```

3. **Avoid writing to image directories**:
   - Write to `/tmp` or volumes
   - Don't write to `/usr`, `/bin` (image layers)

**Storage Driver Impact**:

**overlay2** (default):
- Fast CoW (native kernel support)
- Efficient for most workloads

**devicemapper** (legacy):
- Slower CoW
- Block-level copying

**For SRE**:
- **Monitoring**: Watch for CoW overhead in I/O metrics
- **Optimization**: Use volumes for write-heavy workloads
- **Debugging**: `docker diff <container>` shows changes
- **Performance**: Consider storage driver choice

**Real-World Impact**:

**Database containers**:
- Write-heavy → Use volumes (bypass CoW)
- CoW overhead significant for databases

**Application logs**:
- Many small writes → Use volumes or tmpfs
- CoW overhead for log files

**Configuration files**:
- Rare writes → CoW acceptable
- Bind mount for development

**Best Practices**:
- Use volumes for databases, logs, caches
- Minimize writes to container filesystem
- Monitor I/O performance
- Choose appropriate storage driver

---

## 4. Performance & Optimization

### Q11: How do you optimize Docker image build time and image size?

**A:** **Image optimization** is crucial for faster builds and smaller images.

**Build Time Optimization**:

1. **Layer Caching**:
   ```dockerfile
   # Order matters: Stable layers first
   COPY requirements.txt .        # Changes rarely
   RUN pip install -r req.txt     # Cached if req.txt unchanged
   COPY . .                       # Changes frequently
   ```

2. **Multi-stage Builds**:
   ```dockerfile
   # Build stage (can be large)
   FROM python:3.11 AS builder
   RUN pip install --user -r requirements.txt
   
   # Runtime stage (small)
   FROM python:3.11-slim
   COPY --from=builder /root/.local /root/.local
   # Final image much smaller
   ```

3. **BuildKit Cache Mounts**:
   ```dockerfile
   RUN --mount=type=cache,target=/root/.cache/pip \
     pip install -r requirements.txt
   # Cache persists between builds
   ```

4. **Parallel Builds**:
   - Build multiple images in parallel
   - Use CI/CD parallel jobs

5. **.dockerignore**:
   ```
   # Exclude unnecessary files
   .git
   node_modules
   *.log
   ```
   - Reduces build context size
   - Faster upload to daemon

**Image Size Optimization**:

1. **Use Slim Base Images**:
   ```dockerfile
   # BAD: 900MB
   FROM python:3.11
   
   # GOOD: 150MB
   FROM python:3.11-slim
   ```

2. **Multi-stage Builds**:
   - Remove build tools from final image
   - Only copy necessary artifacts

3. **Combine RUN Commands**:
   ```dockerfile
   # BAD: Multiple layers
   RUN apt-get update
   RUN apt-get install -y curl
   RUN apt-get clean
   
   # GOOD: Single layer
   RUN apt-get update && \
       apt-get install -y curl && \
       apt-get clean && \
       rm -rf /var/lib/apt/lists/*
   ```

4. **Remove Unnecessary Files**:
   ```dockerfile
   RUN apt-get install -y package && \
       rm -rf /var/lib/apt/lists/* && \
       rm -rf /tmp/*
   ```

5. **Use distroless Images**:
   ```dockerfile
   FROM gcr.io/distroless/python3
   # Minimal base (no shell, no package manager)
   ```

**Advanced Techniques**:

1. **BuildKit Features**:
   ```dockerfile
   # syntax=docker/dockerfile:1.4
   RUN --mount=type=cache,target=/root/.cache \
     pip install -r requirements.txt
   ```

2. **Squash Layers** (not recommended):
   ```bash
   docker build --squash .
   # Reduces layers but loses cache benefits
   ```

3. **Image Analysis**:
   ```bash
   # Analyze image layers
   docker history <image>
   
   # Check image size
   docker images
   
   # Dive into image
   dive <image>  # Tool for analyzing images
   ```

**For SRE**:
- **CI/CD**: Optimize Dockerfile for cache hits
- **Storage**: Smaller images = faster pulls
- **Security**: Fewer layers = smaller attack surface
- **Cost**: Smaller images = less storage/bandwidth

**Metrics**:
- **Build time**: Measure and optimize slowest stages
- **Image size**: Track over time, set limits
- **Cache hit rate**: Monitor in CI/CD

**Example Optimized Dockerfile**:
```dockerfile
# Multi-stage, optimized
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app.py .
USER appuser
CMD ["python", "app.py"]
```

---

### Q12: How do you monitor and optimize Docker container resource usage (CPU, memory, I/O)?

**A:** **Resource monitoring** is essential for production Docker deployments.

**Monitoring Tools**:

1. **docker stats** (Built-in):
   ```bash
   docker stats
   # Real-time CPU, memory, I/O
   ```

2. **cAdvisor** (Container Advisor):
   - Exposes metrics endpoint
   - Integrates with Prometheus
   - Historical data

3. **Prometheus + cAdvisor**:
   - Collect metrics
   - Alert on thresholds
   - Grafana dashboards

**CPU Monitoring**:

**Metrics**:
- CPU usage (%)
- CPU throttling
- CPU shares/limits

**Optimization**:
```bash
# Set CPU limits
docker run --cpus="1.0" myapp

# Set CPU shares (relative priority)
docker run --cpu-shares=512 myapp
```

**Memory Monitoring**:

**Metrics**:
- Memory usage (current)
- Memory limit
- Memory cache
- OOM kills

**Optimization**:
```bash
# Set memory limit
docker run -m 512m myapp

# Set memory reservation
docker run --memory-reservation=256m myapp

# Set swap
docker run -m 512m --memory-swap=1g myapp
```

**I/O Monitoring**:

**Metrics**:
- Read/write operations
- Read/write bandwidth
- I/O wait time

**Optimization**:
```bash
# Limit I/O bandwidth
docker run --device-read-bps /dev/sda:1mb \
           --device-write-bps /dev/sda:1mb myapp

# Limit IOPS
docker run --device-read-iops /dev/sda:100 \
           --device-write-iops /dev/sda:100 myapp
```

**Resource Limits Best Practices**:

1. **Set Limits**:
   ```yaml
   # docker-compose.yml
   deploy:
     resources:
       limits:
         cpus: '1.0'
         memory: 512M
       reservations:
         cpus: '0.5'
         memory: 256M
   ```

2. **Monitor and Adjust**:
   - Start with generous limits
   - Monitor actual usage
   - Adjust based on metrics

3. **Prevent OOM**:
   - Set memory limits
   - Monitor for OOM kills
   - Adjust limits before OOM

**For SRE**:
- **Alerting**: Set alerts on high CPU/memory
- **Capacity planning**: Track resource trends
- **Optimization**: Identify resource hogs
- **Cost**: Right-size containers

**Troubleshooting**:

**High CPU**:
```bash
# Check CPU usage
docker stats

# Check processes
docker exec <container> top

# Check limits
docker inspect <container> | grep -i cpu
```

**High Memory**:
```bash
# Check memory usage
docker stats

# Check OOM kills
dmesg | grep -i oom
docker inspect <container> | grep -i memory

# Check memory inside container
docker exec <container> free -h
```

**Performance Profiling**:
- Use `perf` for CPU profiling
- Use `strace` for syscall analysis
- Use application profilers (pprof, etc.)

---

## 5. Security & Isolation

### Q13: Explain Docker's security model. How does it isolate containers? What are the attack vectors?

**A:** Docker uses **multiple layers of security** for container isolation.

**Security Layers**:

1. **Linux Namespaces** (Isolation):
   - PID, Network, Mount, UTS, IPC, User namespaces
   - Isolates processes, network, filesystem

2. **cgroups** (Resource Limits):
   - Limits CPU, memory, I/O
   - Prevents resource exhaustion attacks

3. **Capabilities** (Privilege Reduction):
   ```bash
   docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx
   # Drop all, add only needed
   ```

4. **seccomp** (Syscall Filtering):
   - Filters system calls
   - Blocks dangerous syscalls
   - Default profile blocks many syscalls

5. **AppArmor/SELinux** (MAC):
   - Mandatory Access Control
   - Additional access restrictions

6. **User Namespaces** (Root Mapping):
   - Root in container ≠ root on host
   - Maps container UIDs to host UIDs

**Attack Vectors**:

1. **Container Escape**:
   - **Risk**: Container escapes to host
   - **Mitigation**: Keep Docker updated, use non-root, drop capabilities
   - **Example**: CVE-2019-5736 (runc vulnerability)

2. **Privilege Escalation**:
   - **Risk**: Container gains host privileges
   - **Mitigation**: Run as non-root, drop capabilities, use user namespaces
   - **Example**: Mounting host filesystem with privileges

3. **Resource Exhaustion**:
   - **Risk**: DoS via resource exhaustion
   - **Mitigation**: Set resource limits (CPU, memory)
   - **Example**: Fork bomb, memory leak

4. **Image Vulnerabilities**:
   - **Risk**: Vulnerable base images or dependencies
   - **Mitigation**: Scan images, keep updated, use minimal images
   - **Example**: Old base image with CVEs

5. **Secrets in Images**:
   - **Risk**: Secrets hardcoded in images
   - **Mitigation**: Use secrets management, don't commit secrets
   - **Example**: API keys in Dockerfile

6. **Network Attacks**:
   - **Risk**: Container-to-container attacks
   - **Mitigation**: Network policies, firewalls, separate networks
   - **Example**: Container scanning other containers

**Security Best Practices**:

1. **Non-Root User**:
   ```dockerfile
   RUN useradd -r appuser
   USER appuser
   ```

2. **Drop Capabilities**:
   ```bash
   docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE
   ```

3. **Read-Only Root Filesystem**:
   ```bash
   docker run --read-only --tmpfs /tmp
   ```

4. **No New Privileges**:
   ```bash
   docker run --security-opt no-new-privileges:true
   ```

5. **Scan Images**:
   ```bash
   trivy image myapp:latest
   ```

6. **Secrets Management**:
   - Use Docker secrets (Swarm)
   - Use external secret managers
   - Never hardcode secrets

**For SRE**:
- **Hardening**: Apply security best practices
- **Scanning**: Regular image scans
- **Updates**: Keep Docker and images updated
- **Monitoring**: Monitor for security events
- **Incident Response**: Have plan for security incidents

**Security Checklist**:
- [ ] Run as non-root
- [ ] Drop unnecessary capabilities
- [ ] Set resource limits
- [ ] Scan images for vulnerabilities
- [ ] Use minimal base images
- [ ] Don't hardcode secrets
- [ ] Use read-only filesystem where possible
- [ ] Keep Docker updated
- [ ] Use network policies
- [ ] Monitor security events

---

### Q14: What is Docker Content Trust? How does image signing work?

**A:** **Docker Content Trust (DCT)** provides image signing and verification to prevent tampering.

**What is Content Trust**:

- **Image Signing**: Sign images with cryptographic keys
- **Verification**: Verify image signatures before pulling
- **Tamper Prevention**: Detect if image was modified

**How It Works**:

**Keys**:
1. **Root Key**: Master key (offline, secure storage)
2. **Tagging Key**: Signs tags (can be online)
3. **Repository Key**: Per-repository key

**Signing Process**:
```bash
# Enable content trust
export DOCKER_CONTENT_TRUST=1

# Build and push (automatically signed)
docker build -t myregistry/myapp:v1.0.0 .
docker push myregistry/myapp:v1.0.0
# Image is signed with tagging key
```

**Verification Process**:
```bash
# Enable content trust
export DOCKER_CONTENT_TRUST=1

# Pull (verifies signature)
docker pull myregistry/myapp:v1.0.0
# Fails if signature invalid or missing
```

**Key Management**:

**Initialize Repository**:
```bash
docker trust key generate mykey
docker trust signer add mykey myregistry/myapp --key mykey.pub
```

**Sign Image**:
```bash
docker trust sign myregistry/myapp:v1.0.0
```

**Inspect Signatures**:
```bash
docker trust inspect myregistry/myapp:v1.0.0
```

**For SRE**:
- **Production**: Enable content trust for production images
- **CI/CD**: Sign images in pipeline
- **Key Management**: Secure root key storage
- **Verification**: Verify all production pulls

**Benefits**:
- **Integrity**: Ensures image not tampered
- **Authenticity**: Verifies image source
- **Compliance**: Meets security requirements

**Limitations**:
- **Performance**: Slight overhead (signature verification)
- **Complexity**: Key management complexity
- **Adoption**: Not all registries support

**Best Practices**:
- Enable content trust in production
- Store root key securely (offline)
- Rotate keys periodically
- Document key management procedures

---

## 6. Production Architecture

### Q15: How do you design a production Docker architecture? What are the key considerations?

**A:** **Production Docker architecture** requires careful planning across multiple dimensions.

**Key Considerations**:

1. **High Availability**:
   - **Multiple instances**: Run multiple container instances
   - **Load balancing**: Distribute traffic
   - **Health checks**: Remove unhealthy instances
   - **Auto-restart**: Restart failed containers

2. **Scalability**:
   - **Horizontal scaling**: Add more containers
   - **Auto-scaling**: Scale based on metrics
   - **Stateless design**: Containers should be stateless
   - **State externalization**: Databases, caches external

3. **Reliability**:
   - **Health checks**: Liveness and readiness probes
   - **Graceful shutdown**: Handle SIGTERM properly
   - **Circuit breakers**: Fail fast, don't cascade
   - **Retries**: Retry transient failures

4. **Observability**:
   - **Logging**: Centralized logging (ELK, Loki)
   - **Metrics**: Prometheus, Datadog
   - **Tracing**: Distributed tracing (Jaeger)
   - **Alerting**: Alert on anomalies

5. **Security**:
   - **Image scanning**: Scan for vulnerabilities
   - **Secrets management**: Don't hardcode secrets
   - **Network policies**: Isolate networks
   - **RBAC**: Role-based access control

6. **Data Management**:
   - **Volumes**: Persistent storage
   - **Backups**: Regular backups
   - **Migrations**: Schema migration strategy
   - **Data locality**: Keep data close to compute

7. **Networking**:
   - **Service discovery**: DNS, service mesh
   - **Load balancing**: Internal and external
   - **Network isolation**: Separate networks per service
   - **Firewall rules**: Restrict access

**Architecture Patterns**:

1. **Microservices**:
   - Each service in own container
   - Independent scaling
   - Service mesh for communication

2. **API Gateway**:
   - Single entry point
   - Routing, authentication, rate limiting
   - Example: nginx, Traefik

3. **Database per Service**:
   - Each service has own database
   - Avoid shared databases
   - Use managed databases when possible

4. **Event-Driven**:
   - Services communicate via events
   - Decoupled architecture
   - Message queues (RabbitMQ, Kafka)

**Example Production Stack**:

```
┌─────────────┐
│ Load Balancer│
└──────┬──────┘
       │
   ┌───┴───┐
   │Gateway│
   └───┬───┘
       │
   ┌───┴─────────────────┐
   │  Service A (x3)     │
   │  Service B (x2)      │
   │  Service C (x2)      │
   └───┬─────────────────┘
       │
   ┌───┴──────────┐
   │   Database   │
   │   (Managed)  │
   └──────────────┘
```

**For SRE**:
- **Design**: Plan for failure (assume things will break)
- **Monitoring**: Monitor everything (metrics, logs, traces)
- **Automation**: Automate operations (deploy, scale, heal)
- **Documentation**: Document architecture and procedures
- **Testing**: Test failure scenarios (chaos engineering)

**Operational Considerations**:
- **Deployment**: Zero-downtime deployments
- **Rollback**: Quick rollback procedures
- **Scaling**: Manual and auto-scaling
- **Maintenance**: Update procedures
- **Disaster Recovery**: Backup and restore procedures

---

### Q16: How do you handle secrets in Docker production environments?

**A:** **Secrets management** is critical for production security.

**Never Do This**:
```dockerfile
# BAD: Hardcoded secrets
ENV DB_PASSWORD=secret123
```

**Secrets Management Options**:

1. **Docker Secrets** (Swarm Mode):
   ```yaml
   # docker-compose.yml (Swarm)
   secrets:
     db_password:
       external: true
   
   services:
     app:
       secrets:
         - db_password
       environment:
         DB_PASSWORD_FILE: /run/secrets/db_password
   ```
   - **Encrypted**: At rest and in transit
   - **Mounts**: As files in `/run/secrets/`
   - **Scope**: Swarm services only

2. **Environment Variables** (Runtime):
   ```bash
   docker run -e DB_PASSWORD=${DB_PASSWORD} myapp
   ```
   - **Pros**: Simple, works everywhere
   - **Cons**: Visible in `docker inspect`, process list
   - **Use**: Development, non-sensitive data

3. **External Secret Managers**:
   - **HashiCorp Vault**: Fetch at runtime
   - **AWS Secrets Manager**: For AWS deployments
   - **Azure Key Vault**: For Azure
   - **Google Secret Manager**: For GCP

4. **Init Containers**:
   - Fetch secrets before main container starts
   - Pass to main container via volumes
   - Common in Kubernetes

5. **Secret Files** (Bind Mount):
   ```bash
   docker run -v /host/secrets:/secrets:ro myapp
   ```
   - **Pros**: Simple, works everywhere
   - **Cons**: File management, permissions
   - **Use**: Development, simple setups

**Best Practices**:

1. **Rotate Regularly**:
   - Change secrets periodically
   - Use short-lived credentials when possible

2. **Least Privilege**:
   - Only give secrets to containers that need them
   - Use different secrets per service

3. **Audit**:
   - Log secret access
   - Monitor for unauthorized access

4. **Encryption**:
   - Encrypt secrets at rest
   - Use TLS for secrets in transit

5. **No Logging**:
   - Don't log secrets
   - Mask secrets in logs

**Example with Vault**:
```python
# Application code
import hvac

client = hvac.Client(url='http://vault:8200')
client.token = os.getenv('VAULT_TOKEN')

secret = client.secrets.kv.v2.read_secret_version(path='database')
db_password = secret['data']['data']['password']
```

**For SRE**:
- **Production**: Use external secret managers
- **Development**: Environment variables OK
- **Rotation**: Automate secret rotation
- **Monitoring**: Monitor secret access
- **Incident Response**: Have secret rotation plan

**Security Checklist**:
- [ ] No secrets in images
- [ ] No secrets in environment variables (production)
- [ ] Use secret managers
- [ ] Rotate secrets regularly
- [ ] Audit secret access
- [ ] Encrypt secrets at rest
- [ ] Use TLS for secrets in transit
- [ ] Don't log secrets

---

## 7. Troubleshooting & Debugging

### Q17: Your container keeps restarting. How do you debug this?

**A:** **Container restart loops** are common issues. Systematic debugging approach:

**Step 1: Check Container Status**:
```bash
docker ps -a
# Look for exit codes, restart counts
```

**Step 2: Check Logs**:
```bash
docker logs <container>
docker logs --tail=100 <container>
docker logs -f <container>  # Follow logs
```

**Step 3: Check Exit Code**:
```bash
docker inspect <container> | grep -i exitcode
# 0 = success, non-zero = error
```

**Step 4: Check Restart Policy**:
```bash
docker inspect <container> | grep -i restart
# Might be restarting due to policy
```

**Step 5: Run Interactively**:
```bash
# Run container interactively to see errors
docker run -it --rm <image> /bin/sh
# Or override command
docker run -it --rm <image> /bin/bash
```

**Step 6: Check Resource Limits**:
```bash
docker stats <container>
# Check if OOM killed (memory limit)
docker inspect <container> | grep -i memory
```

**Step 7: Check Dependencies**:
```bash
# Check if dependencies are available
docker exec <container> ping <dependency>
docker exec <container> curl <dependency>
```

**Common Causes**:

1. **Application Crash**:
   - Check application logs
   - Check for exceptions/errors
   - Verify application code

2. **Missing Dependencies**:
   - Database not available
   - External service down
   - Network connectivity issues

3. **Configuration Errors**:
   - Missing environment variables
   - Invalid configuration
   - Wrong file paths

4. **Resource Limits**:
   - OOM killed (memory limit)
   - CPU throttling
   - Disk space full

5. **Healthcheck Failures**:
   - Healthcheck failing
   - Healthcheck timeout too short
   - Healthcheck endpoint wrong

**Debugging Commands**:

```bash
# Check what's running
docker exec <container> ps aux

# Check network
docker exec <container> netstat -tuln

# Check filesystem
docker exec <container> df -h

# Check environment
docker exec <container> env

# Check if process is running
docker exec <container> pgrep -a <process>
```

**For SRE**:
- **Systematic**: Follow debugging steps methodically
- **Logs**: Always check logs first
- **Reproduce**: Try to reproduce locally
- **Document**: Document common issues and solutions
- **Prevent**: Add healthchecks, proper error handling

**Prevention**:
- Proper healthchecks
- Graceful shutdown handling
- Proper error handling in application
- Resource limits set appropriately
- Dependencies checked before startup

---

### Q18: How do you debug network connectivity issues between containers?

**A:** **Network debugging** requires understanding Docker networking.

**Debugging Steps**:

1. **Verify Containers on Same Network**:
   ```bash
   docker network inspect <network>
   # Check if both containers listed
   ```

2. **Check Container IPs**:
   ```bash
   docker inspect <container> | grep -i ipaddress
   # Verify IPs are on same network
   ```

3. **Test DNS Resolution**:
   ```bash
   docker exec <container> nslookup <other-container>
   docker exec <container> ping <other-container>
   # Should resolve to container IP
   ```

4. **Test Connectivity**:
   ```bash
   docker exec <container> ping <other-container-ip>
   docker exec <container> curl http://<other-container>:<port>
   ```

5. **Check Firewall Rules**:
   ```bash
   iptables -L -n -v
   # Check if rules blocking traffic
   ```

6. **Check Application Listening**:
   ```bash
   docker exec <container> netstat -tuln
   # Verify app listening on correct port
   ```

7. **Check Port Mapping**:
   ```bash
   docker ps
   # Verify port mappings correct
   ```

**Common Issues**:

1. **Different Networks**:
   - Containers on different networks can't communicate
   - **Solution**: Connect containers to same network

2. **DNS Not Resolving**:
   - Container name not resolving
   - **Solution**: Check network membership, DNS config

3. **Port Not Listening**:
   - Application not listening on port
   - **Solution**: Check application config, binding to 0.0.0.0

4. **Firewall Blocking**:
   - iptables rules blocking traffic
   - **Solution**: Check firewall rules, Docker manages iptables

5. **Wrong Port**:
   - Connecting to wrong port
   - **Solution**: Verify port numbers

**Debugging Tools**:

```bash
# Network inspection
docker network inspect <network>

# Container network info
docker inspect <container> | grep -A 20 NetworkSettings

# Test connectivity
docker exec <container> ping <target>
docker exec <container> telnet <target> <port>
docker exec <container> curl -v <url>

# Check DNS
docker exec <container> cat /etc/resolv.conf
docker exec <container> nslookup <name>
```

**For SRE**:
- **Systematic**: Check network → DNS → connectivity
- **Tools**: Use network debugging tools
- **Documentation**: Document network architecture
- **Testing**: Test connectivity in CI/CD
- **Monitoring**: Monitor network metrics

**Prevention**:
- Use service names (not IPs)
- Document network architecture
- Test connectivity in staging
- Use healthchecks
- Monitor network metrics

---

## 8. Docker Swarm

### Q19: Explain Docker Swarm. How does it differ from Kubernetes? When would you use it?

**A:** **Docker Swarm** is Docker's native orchestration platform.

**What is Docker Swarm**:

- **Orchestration**: Manages cluster of Docker hosts
- **Native**: Built into Docker Engine
- **Simple**: Easier than Kubernetes
- **Production-ready**: Used in production

**Swarm Architecture**:

**Nodes**:
- **Manager nodes**: Manage cluster, schedule services
- **Worker nodes**: Run containers

**Services**:
- **Services**: Desired state of containers
- **Tasks**: Individual containers
- **Replicas**: Number of container instances

**Key Features**:

1. **Service Discovery**:
   - Automatic DNS-based service discovery
   - Services accessible by name

2. **Load Balancing**:
   - Built-in load balancing
   - Distributes traffic across replicas

3. **Scaling**:
   - Scale services up/down
   - `docker service scale web=5`

4. **Rolling Updates**:
   - Zero-downtime updates
   - Rollback support

5. **Secrets Management**:
   - Built-in secrets management
   - Encrypted at rest and in transit

6. **Networking**:
   - Overlay networks span nodes
   - Automatic service mesh

**Swarm vs Kubernetes**:

| Feature | Docker Swarm | Kubernetes |
|---------|--------------|------------|
| Complexity | Simple | Complex |
| Learning Curve | Low | High |
| Features | Basic | Extensive |
| Ecosystem | Smaller | Large |
| Use Case | Small-medium | Enterprise |
| Native | Yes (Docker) | No (separate) |

**When to Use Swarm**:

1. **Simple Deployments**:
   - Small to medium deployments
   - Don't need Kubernetes features

2. **Docker-Native**:
   - Already using Docker
   - Want native integration

3. **Easier Learning**:
   - Team familiar with Docker
   - Don't want Kubernetes complexity

4. **Resource Constraints**:
   - Limited resources
   - Swarm lighter than Kubernetes

**When NOT to Use Swarm**:

1. **Enterprise Features**:
   - Need advanced features (RBAC, policies)
   - Large scale deployments

2. **Ecosystem**:
   - Need Kubernetes ecosystem
   - Third-party integrations

3. **Complex Workloads**:
   - StatefulSets, DaemonSets
   - Advanced scheduling

**Basic Swarm Commands**:

```bash
# Initialize swarm
docker swarm init

# Join swarm
docker swarm join --token <token> <manager-ip>:2377

# Create service
docker service create --name web --replicas 3 nginx

# Scale service
docker service scale web=5

# Update service
docker service update --image nginx:1.20 web

# List services
docker service ls

# Inspect service
docker service inspect web
```

**For SRE**:
- **Choice**: Swarm for simplicity, K8s for features
- **Migration**: Can migrate from Swarm to K8s
- **Skills**: Swarm easier to learn
- **Production**: Both production-ready

**Best Practices**:
- Use odd number of managers (3, 5, 7)
- Backup swarm state
- Monitor node health
- Use secrets for sensitive data
- Use healthchecks
- Plan for node failures

---

### Q20: How do you perform zero-downtime deployments in Docker Swarm?

**A:** **Zero-downtime deployments** in Swarm use rolling updates.

**Rolling Update Strategy**:

Swarm performs **rolling updates** by default:
1. Start new containers (new version)
2. Wait for healthcheck to pass
3. Stop old containers
4. Repeat until all updated

**Update Command**:
```bash
docker service update --image myapp:v2.0.0 web
```

**Update Parameters**:

1. **Update Delay**:
   ```bash
   docker service update --update-delay 10s web
   # Wait 10s between updating each task
   ```

2. **Parallel Updates**:
   ```bash
   docker service update --update-parallelism 2 web
   # Update 2 tasks at a time
   ```

3. **Failure Action**:
   ```bash
   docker service update --update-failure-action rollback web
   # Rollback on failure
   ```

4. **Monitor Delay**:
   ```bash
   docker service update --update-monitor 30s web
   # Monitor new tasks for 30s before continuing
   ```

**Healthchecks**:

Essential for zero-downtime:
```yaml
# docker-compose.yml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
```

**Rollback**:

If update fails:
```bash
docker service rollback web
# Rollback to previous version
```

**Best Practices**:

1. **Healthchecks**:
   - Always use healthchecks
   - Test healthcheck endpoint

2. **Gradual Updates**:
   - Use update-delay for gradual rollout
   - Monitor metrics during update

3. **Rollback Plan**:
   - Test rollback procedure
   - Have rollback ready

4. **Monitoring**:
   - Monitor metrics during update
   - Alert on errors

5. **Testing**:
   - Test updates in staging
   - Use canary deployments if possible

**Example Zero-Downtime Update**:

```bash
# Service with 3 replicas
docker service create --name web \
  --replicas 3 \
  --update-delay 10s \
  --update-parallelism 1 \
  --update-failure-action rollback \
  --health-cmd "curl -f http://localhost/health || exit 1" \
  --health-interval 10s \
  nginx:1.19

# Update to new version
docker service update --image nginx:1.20 web

# Swarm will:
# 1. Update replica 1, wait for healthcheck
# 2. Update replica 2, wait for healthcheck
# 3. Update replica 3, wait for healthcheck
# All with zero downtime
```

**For SRE**:
- **Practice**: Test updates in staging
- **Monitor**: Watch metrics during updates
- **Rollback**: Have rollback procedure ready
- **Document**: Document update procedures
- **Automate**: Automate update process

---

## 9. CI/CD & Operations

### Q21: How do you implement a comprehensive CI/CD pipeline for Docker with security scanning, testing, and multi-environment promotion?

**A:** **Comprehensive CI/CD** requires multiple stages and gates.

**Pipeline Stages**:

1. **Build**:
   - Build Docker image
   - Tag with version, git SHA
   - Use BuildKit for faster builds

2. **Test**:
   - Unit tests
   - Integration tests
   - Container tests (can it start?)

3. **Scan**:
   - Security scanning (Trivy, Snyk)
   - SBOM generation
   - Fail on critical vulnerabilities

4. **Tag**:
   - Semantic versioning
   - Git SHA tags
   - Environment tags

5. **Push**:
   - Push to registry
   - Push all tags

6. **Deploy**:
   - Dev: Auto-deploy
   - Staging: Manual approval
   - Prod: Manual approval

**Example GitHub Actions Pipeline**:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          load: true
          tags: myapp:${{ github.sha }}
          build-args: |
            APP_VERSION=${{ github.ref_name }}
            GIT_SHA=${{ github.sha }}
      
      - name: Run tests
        run: |
          docker run --rm myapp:${{ github.sha }} pytest
      
      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          exit-code: '1'
          severity: 'CRITICAL,HIGH'
  
  push-to-registry:
    needs: build-and-test
    if: github.event_name != 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to registry
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            myapp:${{ github.sha }}
            myapp:${{ github.ref_name }}
            myapp:latest
      
      - name: Generate SBOM
        run: |
          trivy image --format cyclonedx myapp:${{ github.sha }} > sbom.json
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v3
        with:
          name: sbom
          path: sbom.json
  
  deploy-dev:
    needs: push-to-registry
    if: github.ref == 'refs/heads/develop'
    environment: dev
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to dev
        run: |
          # Deploy commands
          docker service update --image myapp:${{ github.sha }} web
  
  deploy-staging:
    needs: push-to-registry
    if: github.ref == 'refs/heads/main'
    environment: staging
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: |
          # Deploy commands
  
  deploy-production:
    needs: push-to-registry
    if: github.event_name == 'release'
    environment: production
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # Deploy commands
```

**Security Gates**:

1. **Scanning**:
   - Fail on critical/high vulnerabilities
   - Generate SBOM
   - Check for secrets in images

2. **Approvals**:
   - Manual approval for staging/prod
   - Require reviews
   - Audit trail

3. **Compliance**:
   - Check base image versions
   - Verify non-root user
   - Check resource limits

**Best Practices**:

1. **Fail Fast**:
   - Fail on test failure
   - Fail on scan failure
   - Don't proceed if gates fail

2. **Cache**:
   - Cache Docker layers
   - Cache dependencies
   - Use BuildKit cache mounts

3. **Parallel**:
   - Run tests in parallel
   - Run scans in parallel
   - Optimize pipeline time

4. **Documentation**:
   - Document pipeline stages
   - Document approval process
   - Document rollback procedure

**For SRE**:
- **Automation**: Automate everything possible
- **Security**: Security gates in pipeline
- **Monitoring**: Monitor pipeline success rate
- **Optimization**: Optimize pipeline time
- **Documentation**: Document procedures

---

## 10. Scenario-Based Questions

### Q22: You have a production application running in Docker. Suddenly, all containers start failing with "out of memory" errors. How do you investigate and resolve this?

**A:** **OOM (Out of Memory)** investigation requires systematic approach.

**Investigation Steps**:

1. **Check Container Status**:
   ```bash
   docker ps -a
   # Look for containers with exit code 137 (OOM killed)
   ```

2. **Check Memory Usage**:
   ```bash
   docker stats
   # Check current memory usage
   ```

3. **Check Memory Limits**:
   ```bash
   docker inspect <container> | grep -i memory
   # Check memory limits set
   ```

4. **Check Host Memory**:
   ```bash
   free -h
   # Check host memory availability
   ```

5. **Check OOM Kills**:
   ```bash
   dmesg | grep -i oom
   # Check kernel OOM kills
   journalctl -k | grep -i oom
   ```

6. **Check Container Logs**:
   ```bash
   docker logs <container>
   # Look for memory-related errors
   ```

7. **Check Application Metrics**:
   - Check application memory metrics
   - Check for memory leaks
   - Check for sudden traffic spikes

**Root Causes**:

1. **Memory Leak**:
   - Application leaking memory
   - Check application code
   - Use memory profilers

2. **Traffic Spike**:
   - Sudden increase in traffic
   - More requests = more memory
   - Scale horizontally

3. **Memory Limit Too Low**:
   - Limits set too low
   - Increase memory limits

4. **Host Memory Exhausted**:
   - Host out of memory
   - Check other processes
   - Add more host memory

5. **Memory Not Released**:
   - Application not releasing memory
   - Check garbage collection
   - Check for memory leaks

**Resolution Steps**:

1. **Immediate**:
   ```bash
   # Increase memory limits
   docker update --memory=1g <container>
   
   # Or restart with higher limit
   docker run -m 1g <image>
   ```

2. **Scale Horizontally**:
   ```bash
   # Add more containers
   docker service scale web=5
   ```

3. **Fix Application**:
   - Fix memory leaks
   - Optimize memory usage
   - Add memory monitoring

4. **Add Host Memory**:
   - Increase host memory
   - Or move to larger instance

5. **Monitor**:
   - Set up memory alerts
   - Monitor memory trends
   - Proactive scaling

**Prevention**:

1. **Set Limits**:
   ```bash
   docker run -m 512m <image>
   ```

2. **Monitor**:
   - Monitor memory usage
   - Alert on high usage
   - Track trends

3. **Test**:
   - Load testing
   - Memory profiling
   - Stress testing

4. **Optimize**:
   - Optimize application
   - Fix memory leaks
   - Use efficient data structures

**For SRE**:
- **Monitoring**: Monitor memory usage proactively
- **Alerting**: Alert before OOM
- **Scaling**: Auto-scale based on memory
- **Testing**: Load test for memory usage
- **Documentation**: Document memory requirements

---

### Q23: Your Docker registry is down, but you need to deploy a critical fix. What are your options?

**A:** **Registry outage** requires contingency planning.

**Options**:

1. **Use Cached Images**:
   ```bash
   # Check if image cached locally
   docker images
   
   # If cached, tag and use
   docker tag <cached-image> myapp:v1.0.1
   docker-compose up -d
   ```

2. **Build from Source**:
   ```bash
   # Build image locally from source
   docker build -t myapp:v1.0.1 .
   docker-compose up -d
   ```

3. **Use Backup Registry**:
   ```bash
   # If you have backup registry
   docker pull backup-registry/myapp:v1.0.1
   ```

4. **Export/Import Images**:
   ```bash
   # Export image from another host
   docker save myapp:v1.0.1 > myapp.tar
   # Transfer and import
   docker load < myapp.tar
   ```

5. **Use Alternative Registry**:
   - Docker Hub (if using private registry)
   - Public registry temporarily
   - Cloud registry (ECR, GCR, ACR)

**Prevention**:

1. **Multiple Registries**:
   - Primary and backup registries
   - Mirror images
   - Geographic distribution

2. **Local Cache**:
   - Keep images cached locally
   - Cache in CI/CD
   - Cache on production hosts

3. **Image Export**:
   - Export critical images
   - Store backups
   - Version control for images

4. **Registry Monitoring**:
   - Monitor registry health
   - Alert on outages
   - Have runbook ready

**For SRE**:
- **Planning**: Have contingency plans
- **Backup**: Backup critical images
- **Monitoring**: Monitor registry health
- **Documentation**: Document procedures
- **Testing**: Test recovery procedures

**Best Practices**:
- Use multiple registries
- Cache images locally
- Export critical images
- Monitor registry health
- Have recovery procedures
- Test procedures regularly

---

### Q24: How do you handle database migrations in a containerized, zero-downtime deployment scenario?

**A:** **Database migrations** require careful planning for zero-downtime.

**Migration Strategies**:

1. **Forward-Compatible Migrations**:
   - New code works with old schema
   - Old code works with new schema
   - Migrate data gradually
   - Remove old code later

2. **Dual-Write Pattern**:
   - Write to old and new schema
   - Read from old schema
   - Migrate data in background
   - Switch reads to new schema
   - Remove old schema

3. **Backfill Pattern**:
   - Add new columns (nullable)
   - Deploy new code (writes to both)
   - Backfill data
   - Make new columns required
   - Remove old columns

4. **Separate Migration Job**:
   ```bash
   # Run migration before app deployment
   docker run --rm migrations:v1.0.1
   # Then deploy app
   docker service update --image app:v1.0.1 web
   ```

**Zero-Downtime Migration Process**:

1. **Phase 1: Additive Changes**:
   - Add new columns (nullable)
   - Add new tables
   - Don't remove anything

2. **Phase 2: Deploy New Code**:
   - Deploy code that works with both schemas
   - Code writes to both old and new
   - Code reads from old (or both)

3. **Phase 3: Data Migration**:
   - Migrate existing data
   - Backfill new columns
   - Verify data integrity

4. **Phase 4: Switch Reads**:
   - Switch reads to new schema
   - Monitor for issues
   - Rollback if needed

5. **Phase 5: Cleanup**:
   - Remove old columns/tables
   - Remove dual-write code
   - Final migration

**Example**:

```python
# Old code (v1.0.0)
def create_user(name, email):
    db.execute("INSERT INTO users (name, email) VALUES (?, ?)", name, email)

# New code (v1.0.1) - forward compatible
def create_user(name, email, phone=None):
    # Works with old schema (phone nullable)
    db.execute("INSERT INTO users (name, email, phone) VALUES (?, ?, ?)", 
               name, email, phone)

# Migration
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NULL;

# Later (v1.0.2) - make required
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
```

**Best Practices**:

1. **Idempotent Migrations**:
   - Safe to run multiple times
   - Check before applying
   - Rollback support

2. **Test in Staging**:
   - Test migrations in staging
   - Test rollback procedures
   - Load test with migration

3. **Monitor**:
   - Monitor migration progress
   - Monitor application metrics
   - Alert on errors

4. **Rollback Plan**:
   - Have rollback procedure
   - Test rollback
   - Document rollback steps

**For SRE**:
- **Planning**: Plan migrations carefully
- **Testing**: Test in staging
- **Monitoring**: Monitor during migration
- **Rollback**: Have rollback plan
- **Documentation**: Document procedures

**Tools**:
- Alembic (Python)
- Flyway (Java)
- Liquibase (Java)
- Rails migrations (Ruby)
- Custom migration scripts

---

### Q25: You need to debug a production issue but can't reproduce it locally. The container works fine when you run it manually. How do you investigate?

**A:** **Production debugging** requires systematic approach when local reproduction fails.

**Investigation Steps**:

1. **Compare Environments**:
   ```bash
   # Check environment variables
   docker exec <prod-container> env
   # Compare with local
   docker run <image> env
   ```

2. **Check Resource Limits**:
   ```bash
   # Production limits
   docker inspect <prod-container> | grep -i -A 10 resources
   # Compare with local (might be unlimited)
   ```

3. **Check Network**:
   ```bash
   # Production network
   docker network inspect <prod-network>
   # Check DNS, connectivity
   docker exec <prod-container> nslookup <service>
   ```

4. **Check Logs**:
   ```bash
   # Production logs
   docker logs <prod-container>
   # Look for errors, warnings
   # Check timestamps, patterns
   ```

5. **Check Filesystem**:
   ```bash
   # Check what's different
   docker exec <prod-container> ls -la /
   docker exec <prod-container> df -h
   # Check volumes, mounts
   ```

6. **Check Processes**:
   ```bash
   # Running processes
   docker exec <prod-container> ps aux
   # Compare with local
   ```

7. **Check Timing**:
   - Check if issue time-dependent
   - Check if related to traffic
   - Check if related to other services

8. **Check Metrics**:
   - CPU, memory, I/O metrics
   - Compare with local
   - Look for anomalies

**Debugging Tools**:

1. **Exec into Container**:
   ```bash
   docker exec -it <container> /bin/sh
   # Interactive debugging
   ```

2. **Copy Files**:
   ```bash
   docker cp <container>:/path/file .
   # Copy files for analysis
   ```

3. **Network Debugging**:
   ```bash
   docker exec <container> tcpdump -i any
   # Capture network traffic
   ```

4. **Process Debugging**:
   ```bash
   docker exec <container> strace -p <pid>
   # Trace system calls
   ```

5. **Memory Debugging**:
   ```bash
   docker exec <container> valgrind <app>
   # Memory debugging (if available)
   ```

**Common Differences**:

1. **Environment Variables**:
   - Different values in production
   - Missing variables
   - Wrong values

2. **Resource Limits**:
   - Production has limits
   - Local might be unlimited
   - Causing different behavior

3. **Network**:
   - Different network configuration
   - DNS differences
   - Firewall rules

4. **Data**:
   - Production data different
   - Database state different
   - File system state different

5. **Timing**:
   - Race conditions
   - Timing-dependent bugs
   - Load-related issues

**For SRE**:
- **Systematic**: Follow debugging steps
- **Compare**: Compare environments
- **Tools**: Use debugging tools
- **Document**: Document findings
- **Prevent**: Add monitoring, logging

**Best Practices**:
- Add comprehensive logging
- Add metrics
- Use structured logs
- Add healthchecks
- Monitor proactively
- Document environment differences

---

## Summary

These 25 questions cover advanced Docker topics for SRE/Senior SRE interviews:

✅ **Docker Internals**: Architecture, namespaces, cgroups, storage drivers
✅ **Advanced Networking**: Network drivers, DNS, port mapping
✅ **Storage**: Volumes, CoW, filesystems
✅ **Performance**: Optimization, monitoring, resource management
✅ **Security**: Security model, content trust, secrets
✅ **Production**: Architecture, deployments, operations
✅ **Troubleshooting**: Debugging, network issues, OOM
✅ **Swarm**: Orchestration, zero-downtime deployments
✅ **CI/CD**: Pipelines, security, promotion
✅ **Scenarios**: Real-world problem-solving

**Preparation Tips**:
- Understand concepts deeply (not just memorize)
- Practice explaining concepts clearly
- Prepare examples from experience
- Be ready to discuss trade-offs
- Show systematic problem-solving approach

**Remember**: SRE interviews test not just knowledge, but also:
- Problem-solving approach
- Production experience
- Trade-off analysis
- Communication skills
- Learning ability

Good luck with your interviews! 🚀

