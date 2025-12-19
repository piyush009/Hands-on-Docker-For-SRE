## Docker SRE Hands-on Project

This repository is a **phase-wise, hands-on Docker journey** designed for **SRE interviews** – from absolute basics to advanced, real-world usage.

You will:
- **Build** realistic containers and environments step by step.
- **Practice** commands and patterns SREs actually use.
- **Collect** interview questions and real-world challenge talking points in each phase.

Each phase has:
- **Goal**: What you will learn.
- **Hands-on Tasks**: What to type and build.
- **Interview POV**: Questions you can be asked.
- **Real-world Challenges**: Problems SREs hit in practice and how to discuss them.

---

## Phases Overview

1. **Phase 1 – Docker Fundamentals (Hello Container)**
   - Build and run your first image (simple web service).
   - Understand images, containers, tags, `docker run`, `docker ps`, logs, and exec.

2. **Phase 2 – Image Design & Best Practices**
   - Multi-stage builds, image slimming, layering, `.dockerignore`.
   - Registries, tagging strategies, and caching behavior.

3. **Phase 3 – Docker Networking & Local Environments**
   - User-defined networks, ports, DNS inside Docker.
   - `docker-compose` for multi-service apps (web + db + cache).

4. **Phase 4 – Data & State Management**
   - Volumes, bind mounts, backups, and data migration patterns.
   - Handling upgrades and schema changes with containers.

5. **Phase 5 – Observability, Health, and Debugging**
   - Healthchecks, logs, metrics, and common debugging patterns.
   - Capturing troubleshooting stories for interviews.

6. **Phase 6 – Security, Supply Chain, and Policies**
   - Least-privilege images, scanning, SBOMs, base image choices.
   - Resource limits, capabilities, and isolation topics.

7. **Phase 7 – CI/CD & Production-style Workflows**
   - Building and pushing images in CI.
   - Promotion flows (dev → staging → prod), rollbacks, and versioning.

> We will start with **Phase 1** in this repo and then expand step by step.

---

## How to Use This Repo

- **Follow phases in order** – each phase has its own `README.md` with commands.
- **Actually run commands** on your machine; don’t just read.
- **After each phase**, review the “Interview POV” section and practice answering aloud.

---

## Phase 1 – Start Here

Go to `phase-01-basic-docker/README.md` and follow it step by step.


