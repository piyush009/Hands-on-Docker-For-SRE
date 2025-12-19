## Phase 6 – Security, Supply Chain, and Policies

**Goal**: Master Docker security best practices, supply chain security, image scanning, resource limits, and least-privilege principles. Critical for production SRE work.

We'll build a secure containerized application with security hardening, resource limits, and security scanning.

---

## 1. Prerequisites

- Completed Phases 1-5.
- Understanding of basic security concepts (least privilege, defense in depth).

---

## 2. Project Structure

```
phase-06-security-supply-chain/
├── app.py              # Flask app (same as Phase 5)
├── requirements.txt    # Dependencies
├── Dockerfile          # Secure Dockerfile with best practices
├── Dockerfile.insecure # Example of insecure practices (for comparison)
├── docker-compose.yml  # With resource limits and security policies
├── .dockerignore       # Exclude sensitive files
└── README.md           # This file
```

---

## 3. Security Principles

### 3.1. Defense in Depth

Multiple layers of security:
- **Secure base images**: Use minimal, official, regularly updated images
- **Least privilege**: Run as non-root user, drop capabilities
- **Resource limits**: Prevent resource exhaustion attacks
- **Image scanning**: Detect vulnerabilities in dependencies
- **Network policies**: Limit network access
- **Secrets management**: Never hardcode secrets

### 3.2. Least Privilege

- **Non-root user**: Containers should run as non-root
- **Drop capabilities**: Remove unnecessary Linux capabilities
- **Read-only filesystem**: Mount filesystem as read-only where possible
- **Minimal base images**: Use `-slim` or `-alpine` variants
- **No unnecessary packages**: Don't install debug tools in production

### 3.3. Supply Chain Security

- **Base image trust**: Use official images from trusted sources
- **Image scanning**: Scan for known vulnerabilities
- **SBOM (Software Bill of Materials)**: Track all dependencies
- **Image signing**: Sign images to prevent tampering
- **Version pinning**: Pin specific versions, not `latest`

---

## 4. Secure Dockerfile Best Practices

### 4.1. Base Image Selection

**Good**:
```dockerfile
FROM python:3.11-slim
```

**Better**:
```dockerfile
FROM python:3.11-slim@sha256:abc123...  # Pinned digest
```

**Why**: `-slim` images are smaller (fewer attack surfaces), and digest pinning prevents supply chain attacks.

### 4.2. Non-Root User

**Always run as non-root**:
```dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
```

**Why**: If container is compromised, attacker doesn't have root privileges.

### 4.3. Multi-Stage Builds

Use multi-stage builds to exclude build tools from final image:
```dockerfile
FROM python:3.11-slim AS builder
# Install build dependencies
RUN pip install --user ...

FROM python:3.11-slim
COPY --from=builder /root/.local /home/appuser/.local
USER appuser
```

**Why**: Smaller images, fewer vulnerabilities.

### 4.4. Layer Ordering for Security

- Copy dependency files first (for caching)
- Install dependencies
- Copy application code last
- Don't copy secrets or sensitive files

### 4.5. Use .dockerignore

Exclude sensitive files:
```
.env
*.key
*.pem
.git
```

---

## 5. Resource Limits

### 5.1. Memory Limits

Prevent memory exhaustion attacks:
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

Or via `docker run`:
```bash
docker run -m 512m --memory-reservation=256m ...
```

### 5.2. CPU Limits

Prevent CPU exhaustion:
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
    reservations:
      cpus: '0.5'
```

### 5.3. Why Resource Limits Matter

- **Prevent DoS**: Attackers can't exhaust host resources
- **Fairness**: Multiple containers share resources fairly
- **Predictability**: Know resource usage upfront
- **Cost control**: Prevent runaway costs

---

## 6. Image Scanning

### 6.1. Using Docker Scout (Built-in)

Docker Desktop includes Docker Scout for vulnerability scanning:

```bash
# Scan image
docker scout cves phase6-flask:secure

# Compare images
docker scout compare phase6-flask:secure phase6-flask:insecure

# View recommendations
docker scout recommendations phase6-flask:secure
```

### 6.2. Using Trivy (Popular Open Source)

```bash
# Install Trivy (example for Windows with Chocolatey)
# choco install trivy

# Scan image
trivy image phase6-flask:secure

# Scan with JSON output
trivy image -f json -o report.json phase6-flask:secure

# Scan filesystem
trivy fs .

# Scan docker-compose
trivy compose docker-compose.yml
```

### 6.3. Integrating Scanning into CI/CD

Scan images in CI/CD pipeline:
```yaml
# Example GitHub Actions
- name: Build image
  run: docker build -t myapp:${{ github.sha }} .
  
- name: Scan image
  run: trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:${{ github.sha }}
```

**Policy**: Fail build if critical or high vulnerabilities found.

---

## 7. Security Policies

### 7.1. Read-Only Root Filesystem

Mount root filesystem as read-only (if app allows):
```yaml
services:
  web:
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

**Why**: Prevents attackers from writing files, installing malware.

### 7.2. Drop Capabilities

Remove unnecessary Linux capabilities:
```yaml
services:
  web:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed to bind to port < 1024
```

**Why**: Reduces attack surface.

### 7.3. No New Privileges

Prevent privilege escalation:
```yaml
services:
  web:
    security_opt:
      - no-new-privileges:true
```

**Why**: Prevents processes from gaining additional privileges.

### 7.4. User Namespace

Isolate container users from host users:
```yaml
services:
  web:
    userns_mode: "host"  # Or use user namespace remapping
```

**Why**: Even if container is compromised, host user IDs are isolated.

---

## 8. Secrets Management

### 8.1. Never Hardcode Secrets

**Bad**:
```dockerfile
ENV DB_PASSWORD=secret123
```

**Good**: Use environment variables at runtime:
```yaml
services:
  web:
    environment:
      DB_PASSWORD: ${DB_PASSWORD}  # From .env or secret manager
```

### 8.2. Docker Secrets (Swarm Mode)

For Docker Swarm:
```yaml
secrets:
  db_password:
    external: true

services:
  web:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
```

### 8.3. External Secret Managers

For production:
- **HashiCorp Vault**: Fetch secrets at runtime
- **AWS Secrets Manager**: For AWS deployments
- **Azure Key Vault**: For Azure deployments
- **Google Secret Manager**: For GCP deployments

**Best Practice**: Rotate secrets regularly, use short-lived credentials.

---

## 9. Supply Chain Security

### 9.1. Base Image Trust

- **Use official images**: From Docker Hub official repositories
- **Verify signatures**: Use Docker Content Trust
- **Pin digests**: Use `@sha256:...` instead of tags
- **Regular updates**: Keep base images updated

### 9.2. SBOM (Software Bill of Materials)

Generate SBOM to track all dependencies:

```bash
# Using Syft
syft docker:phase6-flask:secure -o json > sbom.json

# Using Trivy
trivy image --format cyclonedx phase6-flask:secure > sbom.json
```

**Why**: Know exactly what's in your image, track vulnerabilities, compliance.

### 9.3. Image Signing

Sign images to prevent tampering:

```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Build and push (will be signed)
docker build -t myregistry/myapp:v1 .
docker push myregistry/myapp:v1
```

**Why**: Ensures image hasn't been tampered with.

---

## 10. Hands-On: Build Secure Image

### 10.1. Build Secure Image

```bash
cd phase-06-security-supply-chain
docker build -t phase6-flask:secure -f Dockerfile .
```

### 10.2. Scan for Vulnerabilities

```bash
# Using Docker Scout (if available)
docker scout cves phase6-flask:secure

# Or using Trivy
trivy image phase6-flask:secure
```

### 10.3. Run with Resource Limits

```bash
docker-compose up --build
```

Check resource limits:
```bash
docker stats phase6-web
```

### 10.4. Verify Non-Root User

```bash
docker exec phase6-web whoami
# Should output: appuser (not root)

docker exec phase6-web id
# Should show UID/GID of appuser
```

### 10.5. Test Security Policies

```bash
# Try to write to root filesystem (should fail if read-only)
docker exec phase6-web touch /test.txt

# Check capabilities
docker inspect phase6-web | grep -i cap
```

---

## 11. Comparing Secure vs Insecure

### 11.1. Build Insecure Image

```bash
docker build -t phase6-flask:insecure -f Dockerfile.insecure .
```

### 11.2. Compare Images

```bash
# Compare sizes
docker images | grep phase6-flask

# Compare vulnerabilities
docker scout compare phase6-flask:secure phase6-flask:insecure
```

**Observations**:
- Secure image: Smaller, fewer vulnerabilities, non-root user
- Insecure image: Larger, more vulnerabilities, runs as root

---

## 12. Interview POV – Questions from This Phase

### **Conceptual**

**Q: Why should containers run as non-root users?**

**A:** Running as non-root follows the **principle of least privilege** and reduces security risk:

1. **Attack surface reduction**: If container is compromised, attacker doesn't have root privileges. They can't modify system files, install malware, or access host resources easily.

2. **Host protection**: Even if container escapes to host (rare but possible), non-root user limits damage.

3. **Compliance**: Many security standards (PCI-DSS, SOC 2) require non-root execution.

4. **Best practice**: Industry standard for production containers.

**Implementation**: Create non-root user in Dockerfile (`RUN useradd -r appuser`) and switch with `USER appuser`. If app needs to bind to port < 1024, use `cap_add: [NET_BIND_SERVICE]` instead of running as root.

**Q: What is the difference between resource limits and reservations in Docker?**

**A:**
- **Limits**: Maximum resources container can use. Hard cap. If exceeded, container is throttled (CPU) or killed (memory OOM).

- **Reservations**: Guaranteed minimum resources. Docker reserves these resources for the container. Other containers can't use reserved resources.

**Example**:
```yaml
resources:
  limits:
    memory: 512M      # Max 512MB
    cpus: '1.0'       # Max 1 CPU
  reservations:
    memory: 256M      # Guaranteed 256MB
    cpus: '0.5'       # Guaranteed 0.5 CPU
```

**Why it matters**: Limits prevent resource exhaustion attacks and ensure fairness. Reservations ensure critical containers always have resources available.

**Q: How do you handle secrets in containerized applications?**

**A:** Never hardcode secrets in images. Use:

1. **Environment variables**: Pass at runtime via `docker run -e` or `docker-compose.yml`. Use `.env` files (but don't commit them).

2. **Docker Secrets** (Swarm mode): Encrypted secrets mounted as files. Use `secrets:` in docker-compose.

3. **External secret managers**: 
   - HashiCorp Vault: Fetch secrets at runtime via API
   - Cloud providers: AWS Secrets Manager, Azure Key Vault, GCP Secret Manager
   - Fetch secrets in application startup code

4. **Init containers**: Use init containers to fetch secrets before main container starts.

5. **Secrets rotation**: Rotate secrets regularly. Use short-lived credentials where possible.

**Best practice**: I'd use Vault or cloud secret manager in production. Secrets are encrypted at rest, audited, and rotated automatically. Never log secrets or include them in images.

**Q: What is image scanning and why is it important?**

**A:** **Image scanning** analyzes container images for known vulnerabilities (CVEs) in dependencies, base images, and packages.

**Why important**:
- **Security**: Find vulnerabilities before deployment
- **Compliance**: Meet security standards (SOC 2, PCI-DSS)
- **Risk management**: Know your risk exposure
- **Supply chain security**: Detect compromised dependencies

**How it works**: Scanners compare image contents against vulnerability databases (CVE databases). They check:
- Base image vulnerabilities
- Installed packages (apt, pip, npm, etc.)
- Application dependencies

**Tools**: Docker Scout, Trivy, Snyk, Clair, Anchore.

**Process**: Scan images in CI/CD pipeline. Fail builds if critical vulnerabilities found. Regularly scan production images. Keep base images updated.

**Q: Explain the concept of "least privilege" in container security.**

**A:** **Least privilege** means giving containers only the minimum permissions and capabilities needed to function.

**Components**:

1. **Non-root user**: Run as non-root user, not root.

2. **Drop capabilities**: Remove unnecessary Linux capabilities. Start with `cap_drop: [ALL]` and add only what's needed.

3. **Read-only filesystem**: Mount root filesystem as read-only. Use `tmpfs` for writable directories if needed.

4. **Minimal base images**: Use `-slim` or `-alpine` variants. Don't include unnecessary tools.

5. **Network policies**: Limit network access. Only expose necessary ports.

6. **Resource limits**: Set memory and CPU limits to prevent resource exhaustion.

**Why**: Reduces attack surface. If container is compromised, damage is limited. Defense in depth strategy.

**Example**: Web app only needs to bind to port 80, read app files, and connect to database. It doesn't need root, filesystem write access (except logs), or network admin capabilities.

**Q: What is an SBOM and why is it important for supply chain security?**

**A:** **SBOM (Software Bill of Materials)** is a complete list of all components, dependencies, and libraries in a software artifact (like a container image).

**Contents**: Lists all packages, versions, licenses, and dependencies. Like an ingredient list for software.

**Why important**:

1. **Vulnerability tracking**: Know exactly what's in your image. When a CVE is published, you can quickly identify if you're affected.

2. **Compliance**: Required by some regulations (e.g., Executive Order 14028 in US). Shows due diligence.

3. **License compliance**: Track licenses of dependencies to ensure compliance.

4. **Supply chain transparency**: Know your software supply chain. Critical for security.

5. **Incident response**: If a dependency is compromised, SBOM helps identify affected systems quickly.

**Formats**: SPDX, CycloneDX, SWID.

**Tools**: Syft, Trivy, Docker Scout can generate SBOMs.

**Best practice**: Generate SBOM for every image build. Store with images. Use for vulnerability scanning and compliance reporting.

### **Practical / Troubleshooting**

**Q: Your image scan found critical vulnerabilities. How do you remediate?**

**A:** Systematic remediation approach:

1. **Assess risk**: 
   - Is vulnerability exploitable in your environment?
   - Is affected package actually used?
   - What's the CVSS score?

2. **Prioritize**: Focus on critical/high severity vulnerabilities first.

3. **Remediation options**:
   - **Update base image**: Use newer base image version
   - **Update packages**: Update vulnerable packages in Dockerfile
   - **Remove unused packages**: If package isn't needed, remove it
   - **Use alternative**: Replace vulnerable package with secure alternative
   - **Accept risk**: Document why risk is acceptable (rare)

4. **Test**: After updating, rebuild image, scan again, test application.

5. **Deploy**: Deploy updated image through CI/CD.

6. **Monitor**: Set up alerts for new vulnerabilities.

**Example**: Found critical vulnerability in `openssl` in base image. Updated base image from `python:3.11-slim` to `python:3.11.5-slim` (newer version with fix). Rebuilt, rescanned, deployed.

**Q: How do you enforce security policies across all container deployments?**

**A:** Multi-layered approach:

1. **Policy as Code**: Define security policies in code (OPA, Kyverno for K8s, or custom scripts).

2. **CI/CD gates**: 
   - Scan images in CI/CD pipeline
   - Fail builds if critical vulnerabilities found
   - Check for non-root user, resource limits, etc.

3. **Image registry policies**: Configure registry (Docker Hub, ECR, ACR) to block images that don't meet policies.

4. **Runtime policies**: Use admission controllers (K8s) or Docker policies to enforce at runtime.

5. **Compliance scanning**: Regular scans of running containers.

6. **Documentation**: Document security requirements and review in code reviews.

**Tools**: 
- **OPA (Open Policy Agent)**: Policy engine
- **Kyverno**: K8s policy engine
- **Falco**: Runtime security monitoring
- **Trivy/Scout**: Image scanning

**Example**: I'd set up Trivy in CI/CD to scan every image. Fail build if critical vulnerabilities or if running as root. Use OPA policies in K8s to enforce resource limits and security contexts.

**Q: Your container needs to write files, but you want read-only filesystem. How do you handle this?**

**A:** Use read-only root filesystem with writable tmpfs mounts:

```yaml
services:
  web:
    read_only: true
    tmpfs:
      - /tmp          # Writable temp directory
      - /var/tmp      # Writable var temp
      - /app/logs     # If app needs to write logs
```

**Why**: Root filesystem is read-only (prevents malware installation), but app can write to specific directories via tmpfs.

**Alternative**: Use volumes for persistent writes:
```yaml
volumes:
  - app_logs:/app/logs

services:
  web:
    read_only: true
    volumes:
      - app_logs:/app/logs  # Writable volume
```

**Best practice**: Identify what needs to be writable (logs, temp files, cache). Use tmpfs for ephemeral data, volumes for persistent data. Keep root filesystem read-only.

**Q: How do you prevent supply chain attacks (compromised base images or dependencies)?**

**A:** Defense in depth strategy:

1. **Use official images**: Prefer official images from Docker Hub official repositories.

2. **Pin digests**: Use `@sha256:...` instead of tags. Prevents image tampering.

3. **Enable Docker Content Trust**: Sign and verify images.

4. **Scan images**: Regularly scan for vulnerabilities and malware.

5. **SBOM**: Generate and verify SBOMs. Track all dependencies.

6. **Vendor verification**: Verify image sources. Use private registries with access control.

7. **Dependency updates**: Keep base images and dependencies updated. Subscribe to security advisories.

8. **Least privilege**: Even if image is compromised, least privilege limits damage.

9. **Network policies**: Limit network access. Containers shouldn't reach internet unless needed.

10. **Monitoring**: Monitor for suspicious activity (unusual network traffic, file changes).

**Example**: I use official `python:3.11-slim@sha256:...` (pinned digest), scan with Trivy, generate SBOM, enable content trust, and run as non-root. This provides multiple layers of protection.

### **Behavior / Experience-Based**

**Q: Tell me about a time you discovered a security vulnerability in a container image.**

**A:** (Example answer structure)

"I was setting up image scanning in our CI/CD pipeline when Trivy flagged a critical vulnerability in our base image's `openssl` package. The vulnerability allowed remote code execution.

I investigated:
1. Checked if we actually used the vulnerable functionality
2. Found we didn't use it, but risk was still high
3. Checked for updated base image version

I remediated by:
1. Updated base image from `python:3.10-slim` to `python:3.10.8-slim` (patched version)
2. Rebuilt all images
3. Rescanned to verify fix
4. Deployed updated images

I also improved our process:
1. Added automated scanning to CI/CD (fail on critical vulnerabilities)
2. Set up weekly scans of production images
3. Created runbook for vulnerability response

This taught me the importance of regular scanning and keeping base images updated."

**Q: How do you balance security and usability in containerized applications?**

**A:** Balance through risk assessment and practical security:

1. **Risk-based approach**: 
   - Critical systems: Maximum security (read-only FS, minimal capabilities, strict policies)
   - Development: More relaxed (but still secure basics like non-root)

2. **Security by default**: 
   - Default to secure (non-root, resource limits, scanning)
   - Relax only when justified and documented

3. **Documentation**: Document why certain security measures are relaxed (e.g., why root is needed).

4. **Gradual hardening**: Start secure, relax if needed. Easier than hardening later.

5. **Tooling**: Use tools that make security easy (e.g., base images with security defaults).

**Example**: Production containers run as non-root with read-only FS and resource limits. Development containers still run as non-root but have more relaxed policies for debugging. Both are scanned, but production has stricter policies.

**Trade-offs**: 
- Read-only FS: More secure but harder to debug. Use tmpfs for dev.
- Minimal images: More secure but harder to debug. Use debug images for troubleshooting.
- Resource limits: Prevents DoS but might need tuning.

---

## 13. Real-World Challenges & Talking Points (Phase 6)

### **"We need root for this"**

**Challenge**: Developers claim they need root privileges for some functionality.

**Solution**: 
- Investigate why root is needed. Often there's an alternative.
- Use capabilities instead: `cap_add: [NET_BIND_SERVICE]` for ports < 1024
- Use init containers for setup tasks
- Document and justify if root is truly needed (rare)

**How to talk about it**: "I've heard 'we need root' many times. Usually it's for binding to port < 1024 or file permissions. I use capabilities (`NET_BIND_SERVICE`) or fix file permissions in Dockerfile. In rare cases where root is needed, I document why and use `security_opt: no-new-privileges` to prevent privilege escalation."

### **Vulnerability fatigue**

**Challenge**: Image scans show hundreds of vulnerabilities, overwhelming team.

**Solution**: 
- Prioritize by severity (critical/high first)
- Focus on exploitable vulnerabilities in your environment
- Automate remediation where possible (auto-update base images)
- Set realistic SLAs (fix critical in 7 days, high in 30 days)
- Use vulnerability management tools to track and prioritize

**How to talk about it**: "I've seen scans with 500+ vulnerabilities. I prioritize by CVSS score and exploitability. I focus on critical/high first, and use tools to track remediation. I also automate base image updates. This reduces noise and focuses effort on real risks."

### **Legacy applications**

**Challenge**: Legacy apps require root or have security issues, but can't be rewritten.

**Solution**: 
- Use wrapper scripts to drop privileges after startup
- Run in isolated network
- Apply resource limits strictly
- Use security monitoring (Falco) to detect anomalies
- Plan migration to secure architecture

**How to talk about it**: "I've worked with legacy apps that need root. I use wrapper scripts to drop privileges after initialization, apply strict resource limits, and monitor with Falco. I also create migration plan to refactor. This provides security while planning long-term fix."

### **Supply chain compromise**

**Challenge**: Base image or dependency is compromised (e.g., SolarWinds-style attack).

**Solution**: 
- Use image signing and verification (Docker Content Trust)
- Pin digests, not tags
- Monitor for image changes
- Have incident response plan
- Use private registries with access control
- Regular security audits

**How to talk about it**: "Supply chain attacks are a real threat. I use image signing, pin digests, and monitor for changes. I also use private registries with access control and regular audits. If compromise is detected, I have incident response plan to rotate images and investigate impact."

### **Security vs performance**

**Challenge**: Security measures (scanning, policies) slow down development.

**Solution**: 
- Optimize scanning (cache results, parallel scans)
- Use fast scanners (Trivy is fast)
- Scan in parallel with builds
- Use policy-as-code for fast feedback
- Balance: Don't sacrifice security, but optimize process

**How to talk about it**: "Security shouldn't block development. I optimize by caching scan results, using fast scanners, and scanning in parallel. I also use policy-as-code for instant feedback. This keeps security strong without slowing development."

---

## 14. When You're Comfortable

You are ready to move on when you can:
- Write secure Dockerfiles following best practices (non-root, minimal images, proper layering).
- Configure resource limits and understand their impact.
- Scan images for vulnerabilities and remediate issues.
- Explain least-privilege principles and implement them.
- Understand supply chain security (SBOMs, image signing, base image trust).
- Balance security and usability in real-world scenarios.

Next, we'll do **Phase 7 – CI/CD & Production-style Workflows** (building and pushing images in CI, promotion flows, rollbacks, and production deployment patterns).

