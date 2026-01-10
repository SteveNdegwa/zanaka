FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/src/app

RUN apt update && apt install -y --no-install-recommends \
    libpq-dev libssl-dev libffi-dev \
    && apt clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /usr/src/app
USER appuser

EXPOSE 8000
