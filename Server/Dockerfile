FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY app ./app
COPY db ./db

RUN useradd -r -u 10001 bookshelf \
 && mkdir -p /app/uploads \
 && chown -R bookshelf:bookshelf /app/uploads
USER bookshelf

EXPOSE 8000

# Single worker on purpose: the limiter in core/ratelimit.py is in-process, so N
# workers means N independent budgets and an Nx weaker limit.
# --proxy-headers is what keeps request.client.host the real client IP behind nginx;
# without it every request looks like it came from the proxy and all users share
# one rate-limit bucket.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
