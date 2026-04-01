# URL Shortener

> URL Shortener is a tool which allows users to convert their long URLs to small URLs, which helps save space and makes them usable in places where large URLs can't be used.

## Features

- Short URLs
- Easy tracking of number of clicks

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
│   └── batch.py
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
  ┌──┴──┐
  │     │
Redis  PostgreSQL
(source of truth) (persistent backup)
```

### Click Count System

```
User clicks short URL
        │
        ▼
Redis incremented atomically (INCR)
        │
        ▼  ← Stats always read from Redis (single source of truth)
        │
Every 60 seconds:
        │
        ▼
Background batch reads Redis counts
        │
        ▼
PostgreSQL overwritten with Redis values (persistence)
        │
        ▼
On Redis restart → counts reloaded from PostgreSQL
```

### Caching Strategy

```
GET /{short_code}
        │
        ▼
Redis lookup (0.1ms)
        │
   ┌────┴──────────────┐
   │                   │
Hit (99%)          Miss (1%)
   │                   │
Return URL        PostgreSQL lookup (5-10ms)
                       │
                  Cache in Redis (TTL: 1 hour)
                       │
                  Return URL
```

### Connection Pool

```
Incoming requests
        │
        ▼
SQLAlchemy pool (pool_size=5, max_overflow=10)
        │
  ┌─────┴──────┐
  │            │
Persistent   Overflow
(5 max)      (10 max, temporary)
        │
        ▼
PostgreSQL (max 15 simultaneous connections)
```

## Request Flow

### Creating a short URL

```
POST /shorten  {"original_url": "https://google.com"}
     │
     ▼
FastAPI generates short code (e.g. "abc123")
     │
     ▼
Saves to PostgreSQL: abc123 → https://google.com
     │
     ▼
Returns: {"short_url": "http://localhost/abc123"}
```

### Redirecting

```
GET /abc123
     │
     ▼
FastAPI checks Redis first (is abc123 cached?)
     │
  ┌──┴──────────────┐
YES (cache hit)    NO (cache miss)
     │               │
     │          Check PostgreSQL
     │               │
     │          Store in Redis
     │               │
     └──────┬─────────┘
            ▼
     Redirect to original URL (302)
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
  "created_at": "2026-03-30T14:32:44"
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
  "created_at": "2026-03-30T14:32:44"
}
```

## Design Decisions

### Why Redis for caching?

- **Redis** allows fast execution of queries in comparison to a database as it uses main memory.
- I used Redis because its fast execution prevents my database from breaking due to continuous database connection requests and allows users faster execution of requests.

### Why batch writing instead of writing every click to DB?

- Batching service is a service which runs at a given time interval.
- Continuous updates to the database can overwhelm it, so we use Redis to store user clicks and update them to the database in 1 minute intervals.

### Why 302 not 301 for redirects?

- `301` → Permanent redirect. Tells browsers to remember that the URL has shifted permanently.
- If `301` is used, browsers cache the redirect permanently and never hit our server again — click counting breaks entirely.
- `302` → Temporary redirect. Ensures every request reaches our server.

### How do I handle Race Conditions?

Race Condition: The issue was how the previous system was failing to give correct stats for one particular condition during batch recording from Redis to PostgreSQL.

**Scenario:**
- User clicks a URL x8, with previous clicks in DB = 22
- Total click count: 8 + 22 → 30
- Batching starts
- Redis → 0; DB → 22 (query not yet executed)
- `GET /{short_code}/stats` → click count = 22 ❌ (wrong)
- DB gets updated
- `GET /{short_code}/stats` → click count = 30 ✅ (correct)

**Solution:**
- Using Redis as single source of truth
- All clicks are loaded at the beginning from PostgreSQL into Redis
- All interactions between clicks and users treat Redis as the primary database
- Batch system updates click counts in PostgreSQL for persistence as secondary database