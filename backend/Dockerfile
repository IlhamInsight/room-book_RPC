FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . /app/

# Expose ports: 8000 for Django RPC / 5000 for Flask RPC
EXPOSE 8000 5000

# Default command: run database migration and start Flask JSON-RPC Server
CMD ["sh", "-c", "python manage.py migrate --noinput && python rpc_server.py"]
