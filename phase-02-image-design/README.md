## Phase 2 – Image Design & Best Practices

**Goal**: Learn how to design Docker images like an SRE: smaller, faster to build, easier to cache, and safer to run.

We’ll reuse the same simple Flask app from Phase 1 but focus on:
- Image size and layers
- Build cache behavior
- `.dockerignore`
- Basic security (non-root user)
- Tagging and pushing to a registry (conceptually)

---

## 1. Starting Point

In this directory we have:
- `app.py` – same Flask app as Phase 1.
- `requirements.txt` – same Python dependencies.
- `Dockerfile` – improved image design.
- `.dockerignore` – tells Docker what NOT to send into the build context.

You should already be comfortable with:
- Building images (`docker build ...`)
- Running containers (`docker run ...`)
- Inspecting logs and exec-ing into containers.

---

## 2. Understand the Improved Dockerfile

Open `Dockerfile` and note the key improvements compared to Phase 1:

- **Slim base image**: still using `python:3.11-slim` to keep size down.
- **Environment variables**: for Python behavior and app environment.
- **Layer ordering**:
  - Copy `requirements.txt` and install dependencies **before** copying app code.
  - This lets Docker **cache dependency layers** when code changes but deps do not.
- **Non-root user**:
  - Create an `appuser` and run the app as that user instead of `root`.
  - This is a very common SRE/security expectation.
- **.dockerignore**:
  - Prevents sending unnecessary files (like `.git`, `__pycache__`, local venvs) into the build context, making builds faster and images cleaner.

---

## 3. Build and Compare Image Size

From this directory, build the image:

```bash
docker build -t phase2-flask:optimized .
docker images phase2-flask
```

If you still have the Phase 1 image, you can list both:

```bash
docker images | grep phase
```

**Things to notice:**
- Both images use a similar base so size may be close, but:
  - Phase 2 image has fewer unnecessary files due to `.dockerignore`.
  - Layer ordering means future builds should be **faster** when only code changes.

---

## 4. Observe Build Cache Behavior

1. Build once:

```bash
docker build -t phase2-flask:optimized .
```

2. Build again immediately:

```bash
docker build -t phase2-flask:optimized .
```

You should see many steps using **“Using cache”**.

3. Now change **only** `app.py` (e.g., tweak the message or add a field in the JSON), then rebuild:

```bash
docker build -t phase2-flask:optimized .
```

**Notice:**
- Steps up to `pip install -r requirements.txt` should still use cache.
- Only the `COPY app.py` (and later) layers re-run.

This is how **proper Dockerfile ordering** makes repeated builds fast in CI and local dev.

---

## 5. Run as a Non-Root User

Run the container:

```bash
docker run --rm -p 8081:5000 --name phase2-app phase2-flask:optimized
```

In another terminal, exec into the container:

```bash
docker exec -it phase2-app /bin/sh
whoami
id
```

You should see the non-root `appuser` instead of `root`.

This is a **great talking point in interviews**: you understand that containers should generally not run as root unless there’s a very good reason.

Exit with `exit`, and stop the container if needed:

```bash
docker stop phase2-app
```

---

## 6. Tagging and (Conceptual) Pushing to a Registry

For interviews, you should know **how images move to registries**, even if you don’t actually have credentials set up here.

Tag the image as if you were pushing to Docker Hub:

```bash
docker tag phase2-flask:optimized your-dockerhub-username/phase2-flask:optimized
```

To push (conceptual – works if you are logged in and own the repo):

```bash
docker login
docker push your-dockerhub-username/phase2-flask:optimized
```

Mention in interviews that:
- You use **meaningful tags** like `v1.2.3`, `staging`, `prod`.
- You avoid using `latest` alone in production promotion flows.

---

## 7. Interview POV – Questions and Answers (Phase 2)

**Image Design**
- **How can you reduce Docker image size?**  
  Use slimmer base images (e.g., `python:3.11-slim` vs full), remove build tools and caches, combine related `RUN` commands, use `.dockerignore` to exclude unnecessary files, and in more advanced cases use **multi-stage builds** so the runtime image contains only what’s needed to run.

- **Why does the order of Dockerfile instructions matter?**  
  Docker builds layer by layer and uses **cache** when instructions and their inputs haven’t changed; by putting rarely changing steps (like installing dependencies from `requirements.txt`) earlier and more frequently changing code copies later, you maximize cache hits and make builds much faster.

- **What is `.dockerignore` and why is it important?**  
  `.dockerignore` tells Docker which files/folders not to send in the build context; this reduces build time, avoids leaking secrets or large directories (like `.git`, `node_modules`, `__pycache__`), and helps keep images simpler and more reproducible.

**Security & Runtime**
- **Why is running containers as root dangerous?**  
  If a process in the container is compromised while running as root, it has high privilege inside the container and, depending on configuration, could more easily escape or damage the host; running as a non-root user follows least-privilege and limits blast radius.

- **How do you run a container as a non-root user?**  
  In the Dockerfile, create a user/group (e.g., with `useradd`/`adduser`), adjust file ownership/permissions, and then specify `USER appuser` so the main process runs under that account; at runtime you can also override with `docker run --user <uid:gid> ...` if needed.

**Build & Registry Workflow**
- **Explain how Docker’s build cache works.**  
  Each instruction (`FROM`, `RUN`, `COPY`, etc.) becomes a layer; Docker checks if the same instruction with the same inputs was built before and, if so, reuses that layer instead of re-running the step, which is why changing a file that is copied early invalidates all later cache layers.

- **How do you version and tag images for different environments?**  
  A common pattern is to tag by both **immutable version** (e.g., git SHA or semver `1.3.5`) and **environment labels** (e.g., `myapp:1.3.5`, `myapp:staging`, `myapp:prod`), then promote the *same* immutable image through environments by retagging, rather than rebuilding for each stage.

- **What problems can occur if you rely on `latest` tag in production?**  
  Deployments can become non-reproducible and unpredictable, rollbacks are harder because `latest` keeps moving, and debugging issues is difficult when you don’t know exactly which image content is running.

---

## 8. Real-World Challenges & Talking Points (Phase 2)

- **Slow CI builds due to poor Dockerfile design**  
  - Symptoms: Every build re-installs dependencies from scratch even when nothing changed.  
  - How to talk about it: Explain how you reordered Dockerfile steps (install deps before copying app code) to leverage caching and significantly reduce build times.

- **Accidentally shipping secrets or large artifacts**  
  - Examples: `.env` files, SSH keys, large `.git` directories or build artifacts copied into the image.  
  - How to talk about it: Describe how you added a `.dockerignore`, audited the image contents, and introduced rules/policies to prevent secrets from entering images.

- **Security review: running as root in containers**  
  - Scenario: Security team flags containers running as root; you’re asked to fix it.  
  - How to talk about it: You modified the Dockerfile to create/run as a non-root user, adjusted file permissions, and validated nothing broke in runtime – tying this to least-privilege best practice.

---

## 9. When You’re Comfortable

You are ready to move on when you can:
- Explain Docker layers and cache behavior clearly.
- Use `.dockerignore` effectively and justify what you ignore.
- Build images that run as non-root and explain why that matters.
- Describe a sensible tagging/versioning approach for images across environments.

Next, we’ll do **Phase 3 – Docker Networking & Local Environments**: multi-container setups with networks (web + DB), DNS inside Docker, and `docker-compose` for realistic SRE-style local stacks.


