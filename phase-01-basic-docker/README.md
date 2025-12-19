## Phase 1 – Docker Fundamentals (Hello Container)

**Goal**: Be comfortable creating a very simple web app, containerizing it, running it, and inspecting it with core Docker commands. This is the “from scratch” starting point.

We’ll use a **small Python web service (Flask)** to keep things simple and cross-platform.

---

## 1. Prerequisites

- **Docker Desktop** installed and running on your machine.
  - On Windows, ensure you can run:

```bash
docker version
docker ps
```

If these commands work (no “cannot connect to Docker daemon” errors), you’re ready.

---

## 2. Create a Minimal Web App

In this folder we’ll keep a tiny Flask service (`app.py`) and dependencies file (`requirements.txt`).

Files in this phase:
- `app.py` – very small HTTP service.
- `requirements.txt` – Python dependencies.
- `Dockerfile` – how to containerize the app.

### 2.1. Understand the App

Open `app.py` and note:
- It listens on **port 5000**.
- It has at least one health-style endpoint (e.g. `/healthz`) you can use later for checks.

You don’t need to be a Python expert; the main focus here is **what we expose to Docker**.

---

## 3. Write the Dockerfile (First Image)

Open `Dockerfile` and read it top to bottom. Key concepts:
- **Base image**: `python:3.11-slim` (or similar).
- **Working directory** inside the container.
- **Copying** dependencies and app code.
- **Installing** dependencies with `pip install -r requirements.txt`.
- **Exposing** the port (for documentation).
- **Entrypoint/CMD** to run the web server.

### 3.1. Build Your First Image

Run from this directory:

```bash
docker build -t phase1-flask:v1 .
```

Then list images:

```bash
docker images
```

**Things to notice:**
- Image `REPOSITORY` should be `phase1-flask` with `TAG` `v1`.
- Size of the image (in MB) – we’ll talk about this in later phases.

---

## 4. Run and Explore the Container

### 4.1. Run the container

```bash
docker run --rm -p 8080:5000 --name phase1-app phase1-flask:v1
```

- `--rm`: auto-remove the container when it exits.
- `-p 8080:5000`: map host port 8080 to container port 5000.
- `--name phase1-app`: give the container a friendly name.

Visit in your browser:

- `http://localhost:8080/`
- `http://localhost:8080/healthz`

You should see responses from the containerized app.

### 4.2. Observe from another terminal

Open another terminal and run:

```bash
docker ps
docker logs phase1-app
```

To exec into the running container:

```bash
docker exec -it phase1-app /bin/sh
```

Inside the container, explore:

```bash
pwd
ls
ps aux
```

Exit with `exit`.

Stop the container (from another terminal if you ran it without `--rm` or in detached mode):

```bash
docker stop phase1-app
```

---

## 5. Common Variations (Practice)

Try these:

- Run in detached mode:

```bash
docker run -d -p 8080:5000 --name phase1-app phase1-flask:v1
```

- Start, stop, restart:

```bash
docker stop phase1-app
docker start phase1-app
docker restart phase1-app
```

- Remove a stopped container:

```bash
docker rm phase1-app
```

- Retag the image:

```bash
docker tag phase1-flask:v1 phase1-flask:latest
docker images
```

---

## 6. Clean-up Commands

Useful for keeping your machine clean:

```bash
docker ps -a           # all containers
docker images          # all images

docker rm <id-or-name>          # remove container
docker rmi <image-id-or-name>   # remove image
```

To remove dangling images and stopped containers:

```bash
docker system prune
```

Be careful – read the prompt before confirming.

---

## 7. Interview POV – Questions from This Phase

**Conceptual**
- **What is the difference between an image and a container?**  
  An **image** is an immutable template (filesystem + metadata) used to create containers; a **container** is a running (or stopped) instance of that image with its own writable layer, process, and configuration.
- **What happens under the hood when you run `docker run`?**  
  Docker pulls or locates the image, creates a container filesystem (adding a writable layer), sets up namespaces and cgroups, configures networking/port mappings, injects env and mounts, then starts the specified process (`CMD`/`ENTRYPOINT`) as PID 1 inside that container.
- **Explain port mapping in Docker (`-p 8080:5000`).**  
  It tells Docker to listen on **host** port `8080` and forward traffic to **container** port `5000`, where the app is actually listening; the app itself only needs to bind to `0.0.0.0:5000` inside the container.
- **What is the purpose of a base image in a Dockerfile?**  
  The base image provides the starting OS/runtime layers (e.g., Linux + Python) so you don’t have to build everything from scratch; it strongly affects image size, security surface, and available tooling.
- **What is the difference between `CMD` and `ENTRYPOINT`?**  
  `ENTRYPOINT` defines the main executable for the container, while `CMD` provides default arguments (or a default command) that can be overridden; commonly you set a fixed `ENTRYPOINT` and vary behavior via `CMD` or runtime args.

**Practical / Troubleshooting**
- **You ran a container but nothing responds on `localhost:8080`. How would you debug?**  
  I would **(1)** check the container state with `docker ps`, **(2)** view logs with `docker logs`, **(3)** `docker exec` into the container to confirm the process is running and listening on the expected port (`netstat`/`ss`), and **(4)** verify the app is bound to `0.0.0.0`, and the port mapping (`-p host:container`) matches the app’s internal port.
- **How do you get a shell inside a running container?**  
  Use `docker exec -it <container-name-or-id> /bin/sh` (or `/bin/bash` if available) to open an interactive shell.
- **How do you see logs for a container?**  
  Use `docker logs <container-name-or-id>` (optionally `-f` to follow logs in real time).

**Behavior / Experience-Based**
- **Tell me about a time you containerized an existing service. What issues did you face?**  
  A strong answer mentions issues like missing OS packages or Python/Node modules, incorrect working directory, forgetting to expose/bind the right port, and environment variables/config files not being passed in—and then explains how you systematically used logs, `docker exec`, and incremental Dockerfile changes to fix them.

---

## 8. Real-World Challenges & Talking Points (Phase 1)

- **“It works locally but not in the container”**
  - Causes: Hard-coded `localhost` bindings, missing environment variables, different file paths, missing OS packages.
  - How to talk about it: Walk through your systematic debugging – logs, `docker exec`, checking environment, comparing host vs container.

- **Port binding confusion**
  - People often confuse container port vs host port.
  - In interviews, emphasize that **inside the container** the app only knows its own port; Docker handles NAT/port mapping to the host.

- **Image size surprises**
  - Using `python:3.11` vs `python:3.11-slim` can massively change image size.
  - Good talking point for how you learned to care about base images and led to optimization work (covered in Phase 2).

---

## 9. When You’re Comfortable

You are ready to move on when you can:
- Write a basic Dockerfile yourself from scratch.
- Build, run, exec into, and clean up containers **without looking up commands**.
- Clearly explain the difference between image vs container, and port mapping.

Next, we’ll do **Phase 2 – Image Design & Best Practices** and refine this image to be smaller, faster, and more production-friendly.


