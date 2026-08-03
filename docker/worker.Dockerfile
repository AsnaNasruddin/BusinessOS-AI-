# Build context: ./backend (see docker-compose.yml) — same source tree and
# dependencies as backend.Dockerfile, different entrypoint.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"]
