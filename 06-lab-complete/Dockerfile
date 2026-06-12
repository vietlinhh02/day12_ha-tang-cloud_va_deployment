# ============================================================
# Dockerfile — Discord Class Bot (Multi-stage)
# ============================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependencies from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir --user -e .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

RUN groupadd -r bot && useradd -r -g bot -d /app bot

WORKDIR /app

# Copy installed packages từ builder
COPY --from=builder /root/.local /home/bot/.local

# Copy application code
COPY bot/ ./bot/
COPY pyproject.toml .

RUN mkdir -p /app/data
RUN chown -R bot:bot /app

USER bot

ENV PATH=/home/bot/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "bot.main"]
