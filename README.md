# URL Shortener

> URL Shortener is a tool which allows users to convert their long URLs to small URLs, which helps save space and makes them usable in places where large URLs can't be used.

## Features

- Short URLs
- Easy tracking of number of clicks
- Redis as primary source of truth — no database in the request path
- Batch sidecar service syncs to PostgreSQL every 60 seconds
- Race condition-free click counting

## Tech Stack

- `FastAPI`
- `Redis`
- `PostgreSQL`
- `SQLAlchemy ORM`
- `Nginx`
- `Docker`

## File Structure

```
url-shortener
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── cache.py
│   ├── batch.py
│   └── url_exceptions.py
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── requirements.txt
```

## Architecture

```
User/Browser
     │
     ▼
  Nginx          ← reverse proxy, receives all requests on port 80
     │
     ▼
  FastAPI         ← handles all application logic, port 8000
     │
     ▼
  Redis           ← primary source of truth (reads + writes)
     │
  Batch sidecar   ← runs every 60s, syncs Redis → PostgreSQL
     │
  PostgreSQL      ← persistent backup only
```

### V2 Design — Redis as Primary

```
Startup:
PostgreSQL → load all URLs into Redis (warmup)

Every request:
/shorten    → write to Redis Hash + add to dirty Set
/{code}     → read from Redis Hash only
/stats      → read from Redis Hash only

Every 60 seconds (batch sidecar):
SPOP dirty Set → pipeline HGETALL → bulk upsert to PostgreSQL
```

### Click Count System

```
User clicks short URL
        │
        ▼
Redis HINCRBY (atomic increment in Hash)
        │
        ▼  ← Stats always read from Redis (single source of truth)
        │
Every 60 seconds:
        │
        ▼
Batch sidecar reads Redis counts
        │
        ▼
PostgreSQL overwritten with Redis values (persistence)
        │
        ▼
On Redis restart → counts reloaded from PostgreSQL (startup warmup)
```

### Dirty Set — What Gets Synced

```
New URL created → short_code added to dirty Set
Click recorded  → short_code added to dirty Set

Batch job:
SPOP(500) from dirty Set → atomic, no duplicates
→ HGETALL each code from Redis
→ bulk upsert to PostgreSQL
→ on failure → restore codes to dirty Set
```

## Prerequisites

- Docker

## How to Run

Move to `root` path and in CLI run:

```bash
docker-compose build
docker-compose up
```

Access API at: `http://localhost:8000`

## API Endpoints

### POST /shorten

```json
Body:
{
  "original_url": "https://google.com"
}

Response:
{
  "short_code": "abc123",
  "original_url": "https://google.com",
  "short_url": "http://localhost/abc123",
  "created_at": "2026-04-09T14:32:44"
}
```

### GET /{short_code}

```
Response code: 302
Redirects to: original URL
```

### GET /{short_code}/stats

```json
Response:
{
  "short_code": "abc123",
  "original_url": "https://google.com",
  "click_count": 3,
  "created_at": "2026-04-09T14:32:44"
}
```

## Load Test Results

Tested with Locust. All tests use `pool_size=5, max_overflow=10`.

| Version | Users | RPS | Failures | Notes |
|---|---|---|---|---|
| V1 | 100 | 66 | 0% | ✅ |
| V1 | 200 | crashed | 100% | ❌ PostgreSQL pool exhausted |
| V2 | 100 | 65.8 | 0% | ✅ |
| V2 | 200 | 132.5 | 0% | ✅ V1 broke here |
| V2 | 500 | 300.1 | 0% | ✅ |
| V2 | 1000 | 294.4 | 3% | ⚠️ Nginx worker limit |

**V2 breaking point:** Between 500-1000 users. Bottleneck shifted from PostgreSQL connection pool → Nginx single worker dropping connections. Fix: multiple uvicorn workers + Nginx tuning.

## Design Decisions

### Why Redis as primary source of truth?

V1 wrote directly to PostgreSQL on every `/shorten` request. With `pool_size=5`, the connection pool exhausted at 200 concurrent users — 100% failure rate.

V2 eliminates database from the request path entirely. All reads and writes go to Redis first. PostgreSQL only receives data through the batch sidecar. Same `pool_size=5` now handles 500 concurrent users with 0% errors.

### Why a batch sidecar instead of writing every change to DB?

Continuous writes to PostgreSQL under load cause connection pool exhaustion. The batch sidecar decouples write pressure — Redis absorbs all writes instantly, the sidecar syncs to PostgreSQL at its own pace every 60 seconds.

The sidecar uses `SPOP` to atomically pop codes from the dirty Set — no two batch runs can process the same code simultaneously. On failure, codes are restored to the dirty Set for the next run.

### Why 302 not 301 for redirects?

`301` is a permanent redirect — browsers cache it and never hit the server again. This breaks click counting entirely since future requests bypass the service. `302` keeps redirects temporary, ensuring every request reaches the server.

### How do I handle Race Conditions?

**The V1 problem:**
- Redis = 8 pending clicks, PostgreSQL = 22 saved clicks
- Batch starts → Redis cleared → DB not yet updated
- Stats called → shows 22 ❌ (lost 8 clicks temporarily)

**V2 solution — Redis as single source of truth:**
- Stats reads from Redis only — never combines DB + Redis
- PostgreSQL is purely for persistence, never for serving stats
- On startup, counts reload from PostgreSQL into Redis
- Race condition eliminated entirely

### Why use a dirty Set instead of syncing everything?

Only URLs that changed (new or clicked) need syncing. The dirty Set tracks exactly which short codes need a DB update. This avoids loading all Redis data into the batch job — only the changed subset is processed each run.

## Versions

- [v1.0](https://github.com/abhishekabck/url-shortener/releases/tag/v1.0) — Redis cache layer, PostgreSQL primary, breaks at 200 users
- [v2.0](https://github.com/abhishekabck/url-shortener/releases/tag/v2.0) — Redis primary, PostgreSQL backup, handles 500 users, 300 RPS