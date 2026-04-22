# kbgen

AI-powered KB generation for ITSM platforms. One Docker image serves both
a FastAPI backend and a React SPA on port **8004**. Polls resolved tickets,
drafts articles with OpenAI, routes them through HITL review, and pushes
approved drafts back to the ITSM.

**Repo**: https://github.com/beedev/kbgen

---

## Install from Docker (Linux)

The fastest path: clone the repo, build locally, and run with the bundled
GLPI + seed data. You provide only an external **Postgres** (with
`pgvector`) and an **OpenAI API key**.

### 1. Prereqs

```bash
# Docker + Compose V2
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# git
sudo apt install -y git jq   # or: sudo dnf install -y git jq
```

### 2. Clone + configure

```bash
git clone https://github.com/beedev/kbgen.git
cd kbgen
cp .env.example .env
```

Edit `.env` — only two required values:

```dotenv
DATABASE_URL=postgresql+asyncpg://kbgen:<password>@<pg-host>:5432/kbgen
OPENAI_API_KEY=sk-proj-...
```

Don't have Postgres handy? Spin one up on the same box:

```bash
docker run -d --name kbgen-pg \
  -p 5432:5432 \
  -e POSTGRES_DB=kbgen -e POSTGRES_USER=kbgen -e POSTGRES_PASSWORD=kbgen_dev \
  -v kbgen-pg-data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

sleep 5
docker exec kbgen-pg psql -U kbgen -c \
  'CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pgcrypto;'
```

Then point `.env` at it:
```dotenv
# Linux (native Docker): use the host's LAN IP or add host-gateway mapping
DATABASE_URL=postgresql+asyncpg://kbgen:kbgen_dev@host.docker.internal:5432/kbgen
```

### 3. Build + run

```bash
docker compose up -d --build
```

`--build` triggers a first-time multi-stage build (~2 min): Node stage
builds the SPA, Python stage installs deps and copies the bundle into
place. Subsequent `docker compose up -d` is ~10 s.

The stack starts:
- `kbgen-glpi-db`  — MariaDB for GLPI
- `kbgen-glpi`     — GLPI (self-installs on first boot; REST API enabled)
- `kbgen-app`      — kbgen on port 8004

First boot takes ~60 s for GLPI install + kbgen auto-seeding 135
healthcare demo tickets into the freshly-installed GLPI.

### 4. Verify

```bash
curl -s http://localhost:8004/api/health | jq .
# expect {"status":"ok","db":"ok","itsm":"ok","openai":"ok"}

curl -s http://localhost:8004/api/kb/stats | jq .
# tickets_processed: 135 (or climbing as the scheduler runs)
```

Open **http://\<host\>:8004** in a browser.

### 5. Force the first poll if you don't want to wait 60 s

```bash
curl -X POST http://localhost:8004/api/kb/poll/run
```

---

## Install from a pre-built image bundle (air-gapped)

For sites without internet access to the GitHub repo or to Docker Hub.
Someone on a connected machine exports a tarball; the recipient
`docker load`s it.

### Three pre-built Docker images shipped together:

| Image | Size | What's inside |
|---|---|---|
| `kbgen:latest` | ~520 MB | FastAPI backend + React SPA on port 8004 |
| `kbgen/glpi-web:1.0` | ~490 MB | GLPI pre-installed, REST API enabled |
| `kbgen/glpi-db:1.0` | ~440 MB | MariaDB with the 135 healthcare seed tickets + 4 KB articles baked in |

The recipient provides only:
- **Postgres** (14+, with `pgvector` + `pgcrypto` extensions)
- **OpenAI API key**

## Exporting the bundle (you)

On the machine where the three images exist (check with `docker images | grep kbgen`):

```bash
cd /Users/bharath/Desktop/kbgen

# 1. Pack all three images into a single tarball (~1.3 GB).
docker save \
  kbgen:latest \
  kbgen/glpi-web:1.0 \
  kbgen/glpi-db:1.0 \
  -o kbgen-bundle.tar

# 2. Grab the compose file that references those exact tags.
#    (It's already in the repo — docker-compose.bundle.yml)

# 3. Bundle both into one archive for the recipient.
tar czf kbgen-distribution.tgz kbgen-bundle.tar docker-compose.bundle.yml .env.example

ls -lh kbgen-distribution.tgz
```

Ship `kbgen-distribution.tgz` however you want — scp, S3, USB, signed download link.

### Optional: push to a private registry instead of tarball

```bash
docker tag kbgen:latest            registry.yourco.com/kbgen:1.0
docker tag kbgen/glpi-web:1.0      registry.yourco.com/kbgen/glpi-web:1.0
docker tag kbgen/glpi-db:1.0       registry.yourco.com/kbgen/glpi-db:1.0

docker push registry.yourco.com/kbgen:1.0
docker push registry.yourco.com/kbgen/glpi-web:1.0
docker push registry.yourco.com/kbgen/glpi-db:1.0
```

Send the recipient the registry URL + `docker-compose.bundle.yml` edited to point at `registry.yourco.com/...` instead of the local tags.

---

## Importing + running the bundle (recipient on Linux)

### Prereqs

- Linux with Docker 24+ and the Compose V2 plugin
- A reachable Postgres 14+ with `pgvector` enabled
- An OpenAI API key
- ~3 GB free disk

### 1. Prepare Postgres

```bash
psql -h <pg-host> -U postgres <<SQL
CREATE DATABASE kbgen;
CREATE USER kbgen WITH PASSWORD 'kbgen_dev_2026';
GRANT ALL PRIVILEGES ON DATABASE kbgen TO kbgen;
\c kbgen
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT CREATE ON DATABASE kbgen TO kbgen;
GRANT CREATE ON SCHEMA public TO kbgen;
SQL
```

### 2. Unpack the bundle

```bash
tar xzf kbgen-distribution.tgz
docker load -i kbgen-bundle.tar
docker images | grep kbgen
# expect: kbgen:latest, kbgen/glpi-web:1.0, kbgen/glpi-db:1.0
```

### 3. Configure

```bash
cp .env.example .env
# edit .env:
#   DATABASE_URL=postgresql+asyncpg://kbgen:kbgen_dev_2026@<pg-host>:5432/kbgen
#   OPENAI_API_KEY=sk-proj-...
```

If Postgres runs on the **same host** as Docker, use `host.docker.internal`
as the hostname (Docker Desktop) or your host's LAN IP (Linux native).

### 4. Start

```bash
docker compose -f docker-compose.bundle.yml up -d
```

First boot:
1. GLPI DB starts — 135 seed tickets already present (baked into the image)
2. GLPI web starts, API auth verifies healthy
3. kbgen runs Alembic against your Postgres, then serves on port 8004

Watch it come up:

```bash
docker compose -f docker-compose.bundle.yml logs -f kbgen
```

### 5. Verify

```bash
curl -s http://localhost:8004/api/health | jq .
# → {"status":"ok", "db":"ok", "itsm":"ok", ...}

curl -s http://localhost:8004/api/kb/stats | jq .
# → tickets_processed: 135 (or climbing as the scheduler runs)
```

Open **http://\<host\>:8004** in a browser:
- **Dashboard** — KPIs, topic chart, latest drafts
- **Workspace** — every ticket with its kbgen decision; click a row to review + push
- **Search** — semantic search over indexed KB chunks
- **Admin → System Status** — manual poll, ITSM test, pipeline tuning

---

## What the bundle ships

```
kbgen-distribution.tgz
├── kbgen-bundle.tar            # three Docker images
│     ├── kbgen:latest
│     ├── kbgen/glpi-web:1.0
│     └── kbgen/glpi-db:1.0
├── docker-compose.bundle.yml   # compose file using the image tags
└── .env.example                # template for DATABASE_URL + OPENAI_API_KEY
```

---

## Recipient-side operations

```bash
# logs
docker compose -f docker-compose.bundle.yml logs -f kbgen

# stop / start
docker compose -f docker-compose.bundle.yml stop
docker compose -f docker-compose.bundle.yml start

# force a poll cycle
curl -X POST http://localhost:8004/api/kb/poll/run

# tear down (containers gone; images stay)
docker compose -f docker-compose.bundle.yml down

# full wipe (containers + committed GLPI state — recipient loses the 135 seed tickets)
docker compose -f docker-compose.bundle.yml down
docker rmi kbgen:latest kbgen/glpi-web:1.0 kbgen/glpi-db:1.0
```

---

## How the seed data got into the image

On the shipping machine, the live GLPI + MariaDB containers had already
been seeded with 135 healthcare tickets via `scripts/seed_glpi_healthcare.py`.
I used `docker commit` to snapshot both containers into the versioned
images so the recipient boots into a working demo without running the
seeder:

```bash
docker commit --pause=true dxp-glpi-db  kbgen/glpi-db:1.0
docker commit --pause=true dxp-glpi     kbgen/glpi-web:1.0
```

To re-seed or update the bundled data: run the seed script against the
running stack, then re-commit + re-export.

---

## Troubleshooting the recipient is likely to hit

| Symptom | Fix |
|---|---|
| `health.db: "error"` in `/api/health` | Postgres unreachable. Verify `DATABASE_URL`. On Linux hosts running Postgres on the same box, use the host's LAN IP (not `localhost`, which resolves inside the container). |
| `health.itsm: "error"` | GLPI hasn't finished starting. Wait 20s and retry. If it persists, `docker compose logs glpi`. |
| `health.openai: "unconfigured"` | `OPENAI_API_KEY` not set. Check `.env`. |
| Dashboard shows 0 tickets | The bundled GLPI already contains 135 tickets but kbgen's Postgres is fresh — it hasn't polled yet. Wait 60s, or `curl -X POST http://localhost:8004/api/kb/poll/run`. |
| `docker compose up` pulls instead of using local images | Compose tried to pull from Docker Hub because tags matched public names. Ensure `docker images` shows the three `kbgen` tags locally first; compose will use them. Alternatively retag to a private-looking namespace (e.g. `yourco/kbgen:1.0`). |
| Apple Silicon is slow | The GLPI image is amd64 — runs under Rosetta. For production Linux deploys this is a non-issue. |

---

## Reverse-proxy deployment (behind nginx at a sub-path)

By default kbgen serves at the root — `http://host:8004/`. To host it behind
nginx at a sub-path like `https://host/kbgen/`, rebuild the image with a
`BASE_PATH` build arg. The value gets baked into the SPA bundle (via Vite's
`base`) and also made available to the Python service (via the `BASE_PATH`
env var) so FastAPI's OpenAPI/docs URLs and an internal base-path-stripping
middleware both know about it.

### 1. Build the image with the prefix baked in

```bash
docker build -t kbgen:with-prefix --build-arg BASE_PATH=/kbgen .
```

Or via compose:

```yaml
# docker-compose.yml
kbgen:
  build:
    context: .
    args:
      BASE_PATH: /kbgen
```

### 2. Nginx snippet

```nginx
location /kbgen/ {
    # Trailing slash on proxy_pass is load-bearing — it strips the /kbgen/
    # prefix before forwarding, so FastAPI routes match unprefixed paths.
    proxy_pass http://kbgen:8004/;

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /kbgen;

    # Kbgen is pure HTTP — no websockets/SSE — so default buffering is fine.
    proxy_read_timeout  90s;
    proxy_send_timeout  90s;
}
```

### 3. What gets rebuilt vs. what doesn't

- **Rebuild required** to change the path — the prefix is baked into asset
  URLs and SPA routing at Vite build time. Running the same image at a
  different sub-path won't work.
- **Default image unchanged** — building without `BASE_PATH` gives you the
  current root-mounted behaviour byte-for-byte.
- **Direct hits still work** — the image also answers at the prefixed path
  without nginx (handy for health-checking the SPA directly inside a
  cluster), because the Python service strips the prefix itself when the
  proxy hasn't already.

---

## License

See `LICENSE`.
