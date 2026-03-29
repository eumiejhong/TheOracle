FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN ls -la oracle_data/migrations/

CMD sh -c "echo '--- Migration status ---' && python manage.py showmigrations oracle_data && echo '--- Running migrate ---' && python manage.py migrate --noinput --verbosity 2 && echo '--- Migrations complete ---' && python manage.py collectstatic --noinput && gunicorn oracle_backend.wsgi --bind 0.0.0.0:$PORT"
