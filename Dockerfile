FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    curl \
    iputils-ping \
    vim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV FLASK_ENV=development
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=1

USER root

EXPOSE 5000

# Script de arranque
CMD ["python", "app.py"]
