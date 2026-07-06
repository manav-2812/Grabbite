# ─────────────────────────────────────────────────────────────────────────────
# GrabBite — Dockerfile
# Multi-stage build: builder installs deps, runtime is a lean final image.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools needed for psycopg2-binary and Pillow C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps (libpq for psycopg2, libjpeg for Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (excludes anything in .dockerignore)
COPY . .

# Copy Alembic migrations if present; create target dir either way so
# Flask-Migrate / Alembic doesn't error at runtime.
# NOTE: commit your migrations/env.py + migrations/versions/ once initialised.
RUN mkdir -p ../migrations
COPY migrat[i]ons/ ../migrations/


# Create writable upload directory
RUN mkdir -p static/uploads instance \
    && chmod 777 static/uploads instance

# Non-root user for security
RUN addgroup --system grabbite && adduser --system --ingroup grabbite grabbite
RUN chown -R grabbite:grabbite /app
USER grabbite

# Expose the port Waitress will bind to (Railway injects $PORT at runtime)
EXPOSE 8000

# Health check — uses the /healthz liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

# Default start command. Shell form is required so $PORT / $HOST are expanded.
# Railway / Render / Fly.io inject PORT at runtime — exec form ["python","run.py"]
# does NOT expand shell variables, causing "Error: '$PORT' is not a valid port number."
CMD python run.py

