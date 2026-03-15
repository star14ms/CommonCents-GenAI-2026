# Fix Docker "Read-Only File System" on macOS

When `make build` (container) fails with:
```
failed to create rwlayer: mkdir /var/lib/docker/overlay2/...: read-only file system
```

Try these steps in order:

## 1. Switch File Sharing Backend (most common fix)

Docker Desktop 4.34+ uses VirtioFS by default, which can cause read-only errors on some setups.

1. Open **Docker Desktop**
2. **Settings** (gear icon) → **General**
3. Find **"Choose file sharing implementation for your containers"**
4. Change from **VirtioFS** to **gRPC FUSE**
5. Click **Apply & Restart**

Then retry:
```bash
make build-container
```

## 2. Restart Docker

- Quit Docker Desktop completely (right-click tray icon → Quit)
- Start Docker Desktop again
- Wait for it to fully initialize before running `make build-container`

## 3. Free Disk Space

Docker needs several GB for images and build layers.

```bash
# Check free space
df -h

# Remove unused Docker data (images, containers, build cache)
docker system prune -a
```

## 4. Reset Docker to Factory Defaults

If the above fails:

1. Docker Desktop → **Settings** → **Troubleshoot**
2. Click **"Reset to factory defaults"** or **"Clean / Purge data"**
3. Restart Docker

**Warning:** This removes all local images and containers.

## 5. Use Colima (alternative to Docker Desktop)

If Docker Desktop keeps failing, [Colima](https://github.com/abiosoft/colima) is a lightweight alternative:

```bash
brew install colima docker
colima start
# Then run: make build-container
```

## After Docker Works

```bash
cd backend
make build
sam deploy
```

This deploys the full backend (chat + stocks).

## Container 500 Error

If the container deploys but returns 500:
1. **Check CloudWatch Logs** – AWS Console → CloudWatch → Log groups → `/aws/lambda/GenAI-WebServiceFunction`
2. **Python version** – The Dockerfile uses Python 3.12 (matches working zip build)
3. **Platform** – On Mac M1/M2, `DOCKER_DEFAULT_PLATFORM=linux/amd64` is set in the Makefile so the image builds for Lambda's x86_64
