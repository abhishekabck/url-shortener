# State 1 - builder
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt --target=/app/packages

# State 2 - final
FROM python:3.12-slim
WORKDIR /app
# Copy installed packages from builder
COPY --from=builder /app/packages /app/packages
# Copy your code
COPY . .

ENV PYTHONPATH=/app/packages

CMD ["python", "-m", "gunicorn", "app.main:app", \
     "-w", "9", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--worker-tmp-dir", "/dev/shm"]