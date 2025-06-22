FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
 && apt-get install -y netcat-openbsd \
 && pip install --no-cache-dir -r requirements.txt \
 && rm -rf /var/lib/apt/lists/*

COPY app ./app
COPY alembic.ini .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]