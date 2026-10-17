# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1

# WORKDIR /app

# # Install Python dependencies separately so Docker can cache this layer.
# COPY requirements.txt ./
# RUN pip install --upgrade pip \
#     && pip install -r requirements.txt

# # The existing backend imports modules (api, agents, config, etc.) as top-level
# # packages, so the application directory itself is the runtime working directory.
# COPY app/ ./app/

# WORKDIR /app/app

# EXPOSE 8000

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]









FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies separately to support Docker layer caching.
COPY requirements.txt ./
RUN pip --default-timeout=120 install -r requirements.txt

# Copy the application source.
COPY app/ ./app/

# Existing imports use top-level application packages.
WORKDIR /app/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
