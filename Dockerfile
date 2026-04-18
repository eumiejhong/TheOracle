FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libheif-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Preload BGE + CLIP models into the container's HF cache before gunicorn starts so
# the first /listing/api/v1/analyze/ request doesn't trigger a 30s+ download under
# a worker timeout. Models live in /root/.cache/huggingface; Railway's persistent
# disk keeps them across container restarts within a deploy.
CMD sh -c "python manage.py migrate --noinput \
  && python manage.py ensure_tables \
  && python manage.py collectstatic --noinput \
  && python -c 'from oracle_frontend.embeddings import preload_models; print(\"[boot] preloading embedding models...\"); print(preload_models())' \
  && gunicorn oracle_backend.wsgi --bind 0.0.0.0:$PORT --timeout 180 --workers 1 --log-file -"
