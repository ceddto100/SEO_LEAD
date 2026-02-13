FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080

# Run with gunicorn for production
# --timeout 300 gives workflows up to 5 minutes to complete
# --workers 1 keeps memory usage low (workflows are I/O-bound, not CPU-bound)
CMD exec gunicorn server:app \
    --bind 0.0.0.0:$PORT \
    --timeout 300 \
    --workers 1 \
    --threads 2 \
    --access-logfile - \
    --error-logfile -
