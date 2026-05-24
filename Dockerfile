FROM python:3.10-slim

WORKDIR /app

# Install deps before copying source so this layer is cached on dep changes only
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY . .

# Persistent data directory (bind-mounted or named volume in production)
RUN mkdir -p /data /data/backups
