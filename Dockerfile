FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first to leverage layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# So the CI step can wait for the app instead of sleeping blindly
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=6 \
  CMD curl -fsS http://localhost:5000/login || exit 1

CMD ["python", "app.py"]
