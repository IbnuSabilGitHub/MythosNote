# Stage 1: Build frontend assets
FROM node:20-bookworm-slim AS frontend

WORKDIR /app

# Cache dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source files needed for tailwind processing
COPY tailwind.config.js postcss.config.js ./
COPY static/ static/
COPY templates/ templates/
COPY apps/ apps/

RUN npm run build

# Stage 2: Final image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .
# Copy compiled CSS from frontend stage (overwrite the one from host)
COPY --from=frontend /app/static/css/output.css ./static/css/output.css

EXPOSE 8000

CMD ["sh", "-c", "python3 manage.py collectstatic --noinput && python3 manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
