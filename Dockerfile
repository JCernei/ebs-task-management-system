# Build stage
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to create the virtual environment in the project directory
RUN poetry config virtualenvs.in-project true

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv ./.venv

# Copy project files
COPY . .

# Create and set proper permissions for media and static directories
RUN mkdir -p /app/mediafiles /app/staticfiles && \
    chmod -R 755 /app/mediafiles /app/staticfiles

# Create and switch to non-root user
#RUN useradd -m django && \
#    chown -R django:django /app
#USER django

# Expose port
#EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
#CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "4"]