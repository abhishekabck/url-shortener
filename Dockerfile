# State 1 - builder
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target=/app/packages

# State 2 - final
FROM python:3.12-slim
WORKDIR /app
# Copy installed packages from builder
COPY --from=builder /app/packages /app/packages
# Copy your code
COPY . .

ENV PYTHONPATH=/app/packages

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]