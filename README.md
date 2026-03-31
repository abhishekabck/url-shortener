# URL Shortener
> URL Shortener is kind of Tool which allows users convert their long url to a small url which allows users to compromise space and using it in a places where large Url can't be used.

## Features:
> - short_urls
> - Easy tracking of number of clicks

## Tech Stack
> - `FastAPI`
> - `Redis`
> - `PostgreSql`
> - `SqlAlchemy`
> - `ORM`

### File Structure
```
url-shortener
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   └── cache.py
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
  Nginx          ← reverse proxy, receives all requests
     │
     ▼
  FastAPI         ← your backend, handles logic
     │
  ┌──┴──┐
  │     │
Redis  PostgreSQL
(cache) (main DB)
```

## Creating a short URL
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

## Redirecting
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
     Redirect to original URL
```


## Prerequisites
> - docker

## How to run
> - Move to `root` path
> - In Cli Run:
> - `docker-compose build`
> - `docker-compose up`
> - Access API at: `http://localhost:8000`


## API endpoints
```
POST   /shorten        → create short URL
Body: {
    "original_url": "https://google.com"
    }

Response: {
    "short_code": "abc123",
    "original_url": "https://google.com",
    "short_url": "http://localhost/abck123",
    "created_at": "2026-03-30T14:32:44"
}
```
```
GET    /{short_code}   → redirect to original
Response code:302
Redirects to: redirect's original url.
```
```
GET    /{short_code}/stats → how many clicks
Response: {
    "short_code": "abc123",
    "original_url": "https://google.com",
    "click_count": 3,
    "created_at": "2026-03-30T14:32:44"
}
```

# Design Decisions

## Why Redis for caching
> - **Redis** allows fast transaction of queries in comparision to database as it uses main memory for fast Execution.
> - I used Redis because of fastExecution which prevents my database from breaking due to Continuous database connection requests and allows user fast Execution of requests.


## Why batch writing instead of writing every click to DB
> - Batching service is kind of service which runs in given time interval.
> - Continious updates to database breaks it thus we use redis to store user clicks and updates them to database in 1 minute of interval.

## Why 302 not 301 for redirects
> `301` -> Refers to permanent shift which tell browsers to remeber that url have been shifted.
> If `301` is used, browsers cache the redirect permanently and never hit our server again — click counting breaks entirely.
> `302` -> Temporary Redirect.