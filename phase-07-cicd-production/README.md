## Phase 7 – CI/CD & Production-style Workflows

**Goal**: Master CI/CD pipelines for Docker, image promotion workflows (dev → staging → prod), rollback strategies, versioning, and production deployment patterns. Essential for SRE production work.

We'll set up CI/CD pipelines, image tagging strategies, registry workflows, and production deployment patterns.

---

## 1. Prerequisites

- Completed Phases 1-6.
- Basic understanding of CI/CD concepts.
- Access to a container registry (Docker Hub, GitHub Container Registry, or cloud registry).

---

## 2. Project Structure

```
phase-07-cicd-production/
├── app.py              # Flask app
├── requirements.txt    # Dependencies
├── Dockerfile          # Production Dockerfile
├── docker-compose.yml  # Production compose file
├── .github/
│   └── workflows/
│       └── ci-cd.yml   # GitHub Actions workflow
├── scripts/
│   ├── deploy.sh       # Deployment script
│   └── rollback.sh     # Rollback script
└── README.md           # This file
```

**Note**: The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) is designed to work from within this phase directory. If you're using this in a larger repository, you may need to adjust the paths in the workflow file or move the `.github` directory to the repository root.

---

## 3. Image Tagging Strategies

### 3.1. Semantic Versioning

**Format**: `major.minor.patch`

**Examples**:
- `v1.0.0` - Initial release
- `v1.0.1` - Patch (bug fixes)
- `v1.1.0` - Minor (new features, backward compatible)
- `v2.0.0` - Major (breaking changes)

**Best Practice**: Tag every release with semantic version.

### 3.2. Git-Based Tagging

**Common patterns**:
- `git-<short-sha>`: `git-abc1234` (commit SHA)
- `<branch>-<sha>`: `main-abc1234`
- `<tag>-<sha>`: `v1.0.0-abc1234`

**Why**: Traceable to exact code version.

### 3.3. Environment Tags

**Patterns**:
- `dev`, `staging`, `prod`
- `dev-<sha>`, `staging-<sha>`, `prod-<sha>`

**Why**: Easy to identify environment.

### 3.4. Multi-Tagging Strategy

Tag images with multiple tags:
```bash
docker build -t myapp:v1.0.0 -t myapp:latest -t myapp:git-abc1234 .
docker push myapp:v1.0.0
docker push myapp:latest
docker push myapp:git-abc1234
```

**Why**: 
- `v1.0.0`: Specific version
- `latest`: Convenience tag (use carefully)
- `git-abc1234`: Traceability

---

## 4. CI/CD Pipeline Overview

### 4.1. Pipeline Stages

1. **Build**: Build Docker image
2. **Test**: Run tests (unit, integration)
3. **Scan**: Security scanning
4. **Tag**: Tag image appropriately
5. **Push**: Push to registry
6. **Deploy**: Deploy to environment (dev/staging/prod)

### 4.2. Promotion Flow

```
┌─────────┐     ┌──────────┐     ┌─────────┐
│   Dev   │ --> │ Staging  │ --> │   Prod  │
└─────────┘     └──────────┘     └─────────┘
   (auto)         (manual)        (manual)
```

- **Dev**: Auto-deploy on every commit
- **Staging**: Manual promotion after testing
- **Prod**: Manual promotion after staging validation

---

## 5. GitHub Actions Workflow

### 5.1. Basic CI/CD Workflow

See `.github/workflows/ci-cd.yml` for complete example.

**Key steps**:
1. Checkout code
2. Set up Docker Buildx
3. Extract metadata (version, tags)
4. Build image with build args (APP_VERSION, BUILD_DATE, GIT_SHA)
5. Run tests
6. Scan image with Trivy
7. Tag image (multiple tags: version, git SHA, latest)
8. Push to registry
9. Deploy (conditional on branch/environment)

**Note**: The workflow assumes it's running from the repository root. If the workflow is in `phase-07-cicd-production/.github/workflows/`, the context paths are set to `.` (current directory). Adjust paths if your repository structure differs.

### 5.2. Workflow Triggers

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [published]
```

### 5.3. Matrix Builds

Build for multiple platforms:
```yaml
platforms: linux/amd64,linux/arm64
```

---

## 6. Image Registry Workflows

### 6.1. Docker Hub

```bash
# Login
docker login

# Tag for Docker Hub
docker tag myapp:latest username/myapp:v1.0.0

# Push
docker push username/myapp:v1.0.0
```

### 6.2. GitHub Container Registry (ghcr.io)

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag
docker tag myapp:latest ghcr.io/username/myapp:v1.0.0

# Push
docker push ghcr.io/username/myapp:v1.0.0
```

### 6.3. AWS ECR

```bash
# Login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag
docker tag myapp:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0.0
```

---

## 7. Deployment Strategies

### 7.1. Rolling Updates

**Strategy**: Gradually replace old containers with new ones.

**Pros**: Zero downtime, gradual rollout
**Cons**: Two versions running simultaneously

**Implementation**: 
- Deploy new version alongside old
- Gradually shift traffic
- Remove old version when new is stable

### 7.2. Blue-Green Deployment

**Strategy**: Run two identical environments (blue = current, green = new).

**Pros**: Instant rollback, no version mixing
**Cons**: Requires double resources

**Implementation**:
1. Deploy new version to green environment
2. Test green environment
3. Switch traffic from blue to green
4. Keep blue for quick rollback

### 7.3. Canary Deployment

**Strategy**: Deploy new version to small subset, gradually increase.

**Pros**: Low risk, gradual validation
**Cons**: Complex to manage

**Implementation**:
1. Deploy to 10% of traffic
2. Monitor metrics
3. Gradually increase to 50%, 100%
4. Rollback if issues detected

---

## 8. Rollback Strategies

### 8.1. Image Rollback

**Simple**: Deploy previous image version.

```bash
# Deploy previous version
docker-compose up -d --image myapp:v1.0.0
```

### 8.2. Git-Based Rollback

**Strategy**: Revert to previous commit, rebuild, redeploy.

**Pros**: Code and image aligned
**Cons**: Slower (rebuild required)

### 8.3. Registry Tag Rollback

**Strategy**: Keep previous versions tagged, redeploy old tag.

```bash
# Previous version still in registry
docker pull myapp:v0.9.0
docker-compose up -d
```

**Best Practice**: Always keep last N versions in registry.

---

## 9. Versioning Best Practices

### 9.1. Never Use `latest` in Production

**Why**: 
- Unpredictable: `latest` changes over time
- No rollback: Can't rollback to previous `latest`
- No traceability: Don't know what version is running

**Instead**: Use specific versions (`v1.0.0`) or commit SHAs.

### 9.2. Tag Every Build

Tag every build, even if not deploying:
- Enables rollback
- Provides audit trail
- Helps debugging

### 9.3. Immutable Images

**Principle**: Never modify images after build. Build new version instead.

**Why**: 
- Reproducibility
- Traceability
- Predictability

### 9.4. Version Metadata

Include metadata in image:
- Build timestamp
- Git commit SHA
- Build number
- Environment

Access via labels or environment variables.

---

## 10. Production Deployment Patterns

### 10.1. Health Checks Before Traffic

**Pattern**: 
1. Deploy new version
2. Wait for healthcheck to pass
3. Add to load balancer
4. Remove old version

**Why**: Prevents serving traffic to unhealthy containers.

### 10.2. Gradual Traffic Shift

**Pattern**: Gradually shift traffic from old to new version.

**Implementation**: 
- Load balancer weights (90% old, 10% new → 50/50 → 100% new)
- Or use service mesh (Istio, Linkerd)

### 10.3. Automated Rollback Triggers

**Pattern**: Automatically rollback if metrics degrade.

**Triggers**:
- Error rate > threshold
- Latency > threshold
- Healthcheck failures

**Implementation**: Monitoring + automation (e.g., Argo Rollouts, Flagger).

---

## 11. Hands-On: CI/CD Setup

### 11.1. Local Testing

Test Docker build locally:
```bash
cd phase-07-cicd-production

# Build with version metadata
docker build \
  --build-arg APP_VERSION=v1.0.0 \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local") \
  -t phase7-flask:local .

# Run container
docker run -p 8085:5000 phase7-flask:local

# Test version endpoint
curl http://localhost:8085/version
```

### 11.2. Tag Image

```bash
# Tag with version
docker tag phase7-flask:local myregistry/phase7-flask:v1.0.0

# Tag with git SHA (example)
docker tag phase7-flask:local myregistry/phase7-flask:git-abc1234

# Tag with environment
docker tag phase7-flask:local myregistry/phase7-flask:dev
```

### 11.3. Push to Registry

```bash
# Login to registry
docker login

# Push all tags
docker push myregistry/phase7-flask:v1.0.0
docker push myregistry/phase7-flask:git-abc1234
docker push myregistry/phase7-flask:dev
```

### 11.4. Deploy with Specific Version

**Option 1: Using docker-compose with environment variables**
```bash
# Set version and build metadata
export APP_VERSION=v1.0.0
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")

# Build and deploy
docker-compose up -d --build
```

**Option 2: Using deployment script**
```bash
# On Linux/Mac or Git Bash/WSL on Windows
bash scripts/deploy.sh v1.0.0 dev

# On Windows PowerShell, you can use WSL or Git Bash
# Or adapt the script for PowerShell
```

**Option 3: Manual deployment**
```bash
# Build image with version
docker build \
  --build-arg APP_VERSION=v1.0.0 \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg GIT_SHA=$(git rev-parse --short HEAD) \
  -t phase7-flask:v1.0.0 .

# Update docker-compose.yml to use: image: phase7-flask:v1.0.0
docker-compose up -d
```

### 11.5. Rollback

**Option 1: Using rollback script**
```bash
# On Linux/Mac or Git Bash/WSL on Windows
bash scripts/rollback.sh v0.9.0 dev

# On Windows PowerShell, use WSL or Git Bash
# Or adapt the script for PowerShell
```

**Option 2: Manual rollback**
```bash
# Update docker-compose.yml to previous version
# Change: image: phase7-flask:v0.9.0

# Pull and deploy previous version
docker-compose pull
docker-compose up -d
```

**Option 3: Quick rollback with docker-compose**
```bash
# If you have the previous image locally
docker-compose up -d --no-deps web
```

---

## 12. Interview POV – Questions from This Phase

### **Conceptual**

**Q: Explain your Docker image tagging strategy for production.**

**A:** I use a **multi-tagging strategy** for production:

1. **Semantic versioning**: Tag every release with `v<major>.<minor>.<patch>` (e.g., `v1.0.0`). This provides clear versioning and follows industry standards.

2. **Git commit SHA**: Tag with `git-<short-sha>` (e.g., `git-abc1234`). This provides traceability to exact code version and helps debugging.

3. **Environment tags**: Tag with environment for convenience (`dev`, `staging`, `prod`), but **never use these in production**. Production always uses specific versions.

4. **Latest tag**: I tag `latest` for convenience, but **never deploy `latest` in production**. It's only for development.

**Example**: For release v1.0.0 from commit abc1234:
```bash
docker tag myapp:latest myapp:v1.0.0
docker tag myapp:latest myapp:git-abc1234
docker tag myapp:latest myapp:latest
```

**Why**: 
- Specific versions enable rollback
- Git SHA provides traceability
- Multiple tags provide flexibility

**Production**: Always deploy specific version (`v1.0.0`) or git SHA, never `latest`.

**Q: What is the difference between rolling updates, blue-green, and canary deployments?**

**A:** Three deployment strategies with different trade-offs:

1. **Rolling Updates**:
   - **How**: Gradually replace old containers with new ones, one at a time
   - **Pros**: Zero downtime, simple, resource efficient
   - **Cons**: Two versions run simultaneously (can cause issues)
   - **Use when**: Low risk changes, stateless applications

2. **Blue-Green Deployment**:
   - **How**: Run two identical environments. Blue = current, green = new. Switch traffic instantly
   - **Pros**: Instant rollback (just switch back), no version mixing, easy testing
   - **Cons**: Requires double resources, more complex
   - **Use when**: Critical applications, need instant rollback

3. **Canary Deployment**:
   - **How**: Deploy new version to small subset (e.g., 10%), gradually increase if metrics are good
   - **Pros**: Low risk, gradual validation, catch issues early
   - **Cons**: Complex to manage, requires monitoring
   - **Use when**: High-risk changes, need gradual validation

**My approach**: I use rolling updates for most applications, blue-green for critical systems, and canary for high-risk changes. The choice depends on risk tolerance, resource constraints, and application characteristics.

**Q: How do you handle rollbacks in a containerized environment?**

**A:** Multi-layered rollback strategy:

1. **Image-level rollback**: 
   - Keep previous N versions in registry
   - Deploy previous image version: `docker-compose up -d --image myapp:v0.9.0`
   - Fast (seconds), but requires previous versions available

2. **Git-based rollback**:
   - Revert to previous commit
   - Rebuild and redeploy
   - Slower (rebuild time), but ensures code and image alignment

3. **Infrastructure rollback**:
   - If using infrastructure as code (Terraform, CloudFormation), rollback infrastructure changes
   - Use versioned infrastructure configs

4. **Automated rollback**:
   - Set up monitoring (error rate, latency)
   - Automatically rollback if metrics degrade
   - Use tools like Argo Rollouts, Flagger

**Best practices**:
- Always keep last 3-5 versions in registry
- Test rollback procedure regularly
- Document rollback steps in runbooks
- Have rollback decision criteria (when to rollback vs fix forward)

**Example**: If error rate > 5% after deployment, automatically rollback to previous version. Otherwise, investigate and fix forward if possible.

**Q: Why should you never use the `latest` tag in production?**

**A:** **Never use `latest` in production** because:

1. **Unpredictability**: `latest` changes over time. Today's `latest` is different from tomorrow's. You don't know what version you're running.

2. **No rollback**: If `latest` is updated and breaks production, you can't rollback to previous `latest` because it's been overwritten.

3. **No traceability**: Can't trace production issues to specific code version. Debugging becomes difficult.

4. **Deployment inconsistencies**: Different environments might pull different `latest` versions, causing inconsistencies.

5. **Security**: Can't track which version has vulnerabilities. Can't apply security patches to specific versions.

**Instead**: 
- Use semantic versions: `v1.0.0`, `v1.0.1`
- Use git SHAs: `git-abc1234`
- Pin exact versions in production configs

**Exception**: `latest` is fine for development, but production should always use specific versions.

**Q: Explain your CI/CD pipeline for Docker images.**

**A:** My CI/CD pipeline has these stages:

1. **Build**: 
   - Build Docker image using Dockerfile
   - Use BuildKit for faster builds
   - Build for multiple platforms if needed (linux/amd64, linux/arm64)

2. **Test**:
   - Run unit tests
   - Run integration tests (if applicable)
   - Test Docker image (can it start, healthcheck works)

3. **Scan**:
   - Security scan image (Trivy, Snyk, Docker Scout)
   - Fail build if critical vulnerabilities found
   - Generate SBOM

4. **Tag**:
   - Tag with semantic version (`v1.0.0`)
   - Tag with git SHA (`git-abc1234`)
   - Tag with environment (`dev`, `staging`, `prod`)

5. **Push**:
   - Push to container registry (Docker Hub, ECR, GCR, etc.)
   - Push all tags

6. **Deploy** (conditional):
   - Auto-deploy to dev on every commit
   - Manual deploy to staging after testing
   - Manual deploy to prod after staging validation

**Tools**: GitHub Actions, GitLab CI, Jenkins, CircleCI, etc.

**Best practices**:
- Fail fast (fail on test failure, scan failure)
- Parallel stages where possible
- Cache Docker layers
- Use matrix builds for multiple platforms
- Tag every build for traceability

**Q: How do you promote images from dev to staging to production?**

**A:** **Promotion workflow**:

1. **Dev (automatic)**:
   - Every commit triggers build and auto-deploy to dev
   - Tag: `dev-<sha>` or `dev-latest`
   - Fast feedback loop

2. **Staging (manual promotion)**:
   - After testing in dev, manually promote to staging
   - Tag: `staging-<sha>` or `staging-v1.0.0`
   - Run full test suite in staging
   - Validate with production-like data

3. **Production (manual promotion)**:
   - After staging validation, manually promote to production
   - Tag: `prod-v1.0.0` or just `v1.0.0`
   - Deploy during maintenance window (if needed)
   - Monitor closely after deployment

**Implementation**:
- Use registry tags: Same image, different tags for different environments
- Or use separate registries: `dev-registry`, `prod-registry`
- Use CI/CD promotion jobs: Manual approval gates

**Best practices**:
- Never skip environments (dev → staging → prod)
- Require approvals for production
- Keep same image across environments (don't rebuild)
- Tag production deployments with release notes

**Example**: Build once in CI (`v1.0.0`), tag for dev (`dev-v1.0.0`), promote to staging (`staging-v1.0.0`), then production (`prod-v1.0.0`). Same image, different tags.

### **Practical / Troubleshooting**

**Q: Your CI/CD pipeline is slow. How do you optimize it?**

**A:** Optimization strategies:

1. **Docker layer caching**:
   - Order Dockerfile layers (dependencies before code)
   - Use BuildKit cache mounts: `RUN --mount=type=cache`
   - Use registry cache: `--cache-from` in CI

2. **Parallel stages**:
   - Run tests and scans in parallel
   - Build multiple images in parallel (if applicable)

3. **Conditional builds**:
   - Only build if code changed (check git diff)
   - Skip stages if not needed (e.g., skip deploy on PR)

4. **Use faster tools**:
   - Use Trivy (fast scanner) instead of slow scanners
   - Use BuildKit for faster builds

5. **Cache dependencies**:
   - Cache pip/npm packages between builds
   - Use multi-stage builds to cache build dependencies

6. **Optimize Dockerfile**:
   - Use `.dockerignore` to reduce build context
   - Minimize layers
   - Use slim base images

**Example**: Reduced build time from 10 minutes to 3 minutes by:
- Using BuildKit cache mounts for pip packages
- Parallel test execution
- Conditional builds (skip deploy on PRs)
- Using Trivy instead of slow scanner

**Q: How do you handle database migrations in a CI/CD pipeline?**

**A:** **Migration strategy**:

1. **Separate migration job**:
   - Create separate Docker image/job for migrations
   - Run migrations as one-off job: `docker-compose run --rm migrations`
   - Run before deploying new app version

2. **Migration in app startup** (if idempotent):
   - Run migrations as part of app startup
   - Ensure migrations are idempotent (safe to run multiple times)
   - Use migration tools (Alembic, Flyway, etc.)

3. **CI/CD pipeline**:
   ```
   Build app image → Run migration job → Deploy app
   ```

4. **Rollback consideration**:
   - Some migrations are irreversible
   - Plan rollback strategy (forward-compatible migrations)
   - Test migrations in staging first

**Best practices**:
- Always test migrations in staging
- Make migrations idempotent
- Have rollback plan for migrations
- Run migrations before deploying new app version
- Monitor migration execution

**Example**: In CI/CD, after building app image, run migration job (`migrate:v1.0.0`), wait for completion, then deploy app (`app:v1.0.0`). If migration fails, don't deploy app.

**Q: Your production deployment failed. How do you investigate?**

**A:** **Systematic investigation**:

1. **Check deployment status**:
   - Are containers running? (`docker ps`, `kubectl get pods`)
   - What's the exit code? (`docker inspect`)
   - Check deployment logs

2. **Check application logs**:
   - Container logs: `docker logs <container>`
   - Application logs (structured logs)
   - Look for errors, stack traces

3. **Check healthchecks**:
   - Are healthchecks passing? (`docker ps` shows healthy/unhealthy)
   - Manually test healthcheck endpoint

4. **Check metrics**:
   - Error rate (should be low)
   - Latency (should be normal)
   - Resource usage (CPU, memory)

5. **Compare with previous version**:
   - What changed? (code diff, config diff)
   - Did previous version work?
   - Rollback and verify

6. **Check dependencies**:
   - Database connectivity
   - External API availability
   - Network connectivity

7. **Check configuration**:
   - Environment variables correct?
   - Secrets available?
   - Config files valid?

**Decision**: Based on investigation, either:
- **Fix forward**: If issue is minor, fix and redeploy
- **Rollback**: If issue is critical, rollback immediately

**Example**: Deployment failed. Checked logs, found database connection error. Checked database, found it was down. Fixed database, redeployed. If database was fine, would have rolled back app version.

**Q: How do you ensure zero-downtime deployments?**

**A:** **Zero-downtime deployment patterns**:

1. **Health checks before traffic**:
   - Deploy new version
   - Wait for healthcheck to pass
   - Add to load balancer
   - Remove old version

2. **Gradual traffic shift**:
   - Use load balancer weights (90% old, 10% new → gradually shift)
   - Or use service mesh (Istio, Linkerd) for traffic splitting

3. **Multiple instances**:
   - Run multiple instances (at least 2)
   - Deploy new version alongside old
   - Remove old after new is healthy

4. **Readiness probes**:
   - Use readiness probes to prevent traffic to unhealthy containers
   - Only route traffic when ready

5. **Database migrations**:
   - Use forward-compatible migrations
   - Run migrations before deploying new app version
   - Ensure old and new app versions can coexist

**Implementation**:
- Use orchestrators (Kubernetes, Docker Swarm) with rolling updates
- Or use blue-green deployment
- Or use canary deployment

**Monitoring**: Monitor error rate, latency during deployment. Automatically rollback if metrics degrade.

**Example**: Deploy new version with 10% traffic. Monitor for 5 minutes. If metrics good, increase to 50%, then 100%. If metrics degrade, rollback immediately.

### **Behavior / Experience-Based**

**Q: Tell me about a time you had to rollback a production deployment.**

**A:** (Example answer structure)

"I was deploying a new version of our API service. After deployment, we saw error rate spike from 0.1% to 5%. I immediately investigated:

1. Checked application logs - found database connection pool exhaustion
2. Checked database - was healthy, but connection limit reached
3. Reviewed code changes - found we increased connection pool size but didn't update database max_connections

I made decision to rollback:
1. Updated docker-compose to previous version (`v1.0.0` → `v0.9.0`)
2. Pulled previous image
3. Redeployed (took 2 minutes)
4. Error rate returned to normal

After rollback, I:
1. Fixed the issue (updated database config)
2. Tested in staging
3. Redeployed with fix

This taught me to:
- Always monitor metrics during deployment
- Have rollback plan ready
- Test database changes in staging first
- Set up automated rollback triggers"

**Q: How do you balance deployment speed and safety?**

**A:** **Balanced approach**:

1. **Risk-based deployment speed**:
   - **Low risk** (config changes, bug fixes): Faster deployment, automated
   - **High risk** (major features, database changes): Slower, manual approval, canary

2. **Automation with gates**:
   - Automate everything possible (build, test, scan)
   - Manual gates for high-risk changes (production approval)
   - Automated rollback on failure

3. **Gradual rollout**:
   - Use canary for high-risk changes
   - Use blue-green for critical systems
   - Use rolling updates for low-risk changes

4. **Monitoring and feedback**:
   - Monitor metrics during deployment
   - Fast feedback loop (deploy → monitor → decide)
   - Automated alerts

5. **Practice**:
   - Regular deployments (more frequent = less risk per deployment)
   - Test rollback procedures
   - Learn from incidents

**Example**: For bug fixes, I use automated CI/CD with rolling updates (deploy in 5 minutes). For major features, I use canary deployment with manual approval gates (deploy over 30 minutes with gradual traffic shift).

**Trade-off**: Speed vs safety. I optimize for safety for production, speed for development. Use automation to make safe deployments fast.

---

## 13. Real-World Challenges & Talking Points (Phase 7)

### **"We need to deploy faster"**

**Challenge**: Business pressure to deploy faster, but safety is concern.

**Solution**: 
- Automate everything possible (CI/CD)
- Use gradual rollouts (canary) to deploy safely but quickly
- Improve testing (faster tests, better coverage)
- Deploy more frequently (smaller changes = less risk)
- Use feature flags for safe rollouts

**How to talk about it**: "I've balanced speed and safety by automating CI/CD (reduces manual time) and using canary deployments (deploy quickly but safely). I also deploy more frequently with smaller changes, which reduces risk per deployment. This gives us speed without sacrificing safety."

### **Image registry as single point of failure**

**Challenge**: If registry is down, can't deploy.

**Solution**: 
- Use multiple registries (mirror images)
- Cache images locally
- Use CDN for registry
- Have backup registry
- Keep images in multiple regions

**How to talk about it**: "I've mitigated registry risk by using mirrored registries, caching images locally, and keeping images in multiple regions. I also have backup registry configured. This ensures availability even if primary registry fails."

### **Deployment conflicts**

**Challenge**: Multiple teams deploying simultaneously, causing conflicts.

**Solution**: 
- Use deployment locks/scheduling
- Coordinate deployments
- Use feature flags instead of code deployments
- Stagger deployments
- Use deployment windows

**How to talk about it**: "I've managed deployment conflicts by using deployment locks, coordinating with teams, and using feature flags for non-breaking changes. For critical systems, we use deployment windows. This prevents conflicts and reduces risk."

### **Version drift across environments**

**Challenge**: Different environments running different versions, causing inconsistencies.

**Solution**: 
- Use same image across environments (different tags)
- Don't rebuild for each environment
- Use infrastructure as code for consistency
- Regular sync checks
- Document versions

**How to talk about it**: "I prevent version drift by using same images across environments (just different tags), using infrastructure as code, and regular sync checks. I also document versions in each environment. This ensures consistency and makes debugging easier."

### **Rollback takes too long**

**Challenge**: Rollback procedure is manual and slow.

**Solution**: 
- Automate rollback procedures
- Keep previous versions readily available
- Use blue-green for instant rollback
- Practice rollback regularly
- Document and script rollback

**How to talk about it**: "I've automated rollback procedures and keep previous versions in registry. I use blue-green deployment for critical systems (instant rollback). I also practice rollback regularly and have scripts ready. This reduces rollback time from 10 minutes to 30 seconds."

---

## 14. When You're Comfortable

You are ready when you can:
- Set up CI/CD pipelines for Docker images (GitHub Actions, GitLab CI, etc.).
- Implement image tagging strategies (semantic versioning, git-based, multi-tagging).
- Design promotion workflows (dev → staging → prod).
- Execute rollback procedures quickly and safely.
- Choose appropriate deployment strategies (rolling, blue-green, canary).
- Balance deployment speed and safety.
- Handle production deployment incidents.

---

## 15. Congratulations! 🎉

You've completed all 7 phases of the Docker SRE hands-on project! You now have:

✅ **Fundamentals**: Basic Docker commands and concepts
✅ **Best Practices**: Image design, optimization, security
✅ **Networking**: Multi-container apps, Docker Compose
✅ **State Management**: Volumes, backups, migrations
✅ **Observability**: Logging, metrics, healthchecks, debugging
✅ **Security**: Least privilege, scanning, supply chain
✅ **Production**: CI/CD, deployments, rollbacks

**Next Steps**:
- Practice these concepts in real projects
- Contribute to open-source containerized projects
- Build your own containerized applications
- Prepare for SRE interviews using the interview Q&A sections
- Keep learning: Kubernetes, service mesh, advanced orchestration

**Remember**: The best way to learn is by doing. Keep building, deploying, and learning!

