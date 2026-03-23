# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Set timezone
ENV TZ=Europe/Berlin

WORKDIR /app/pv_rm_interface 
ENV PYTHONPATH=/app

# Update & install any required packages
RUN apt-get update && apt-get install -y \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy both device specific package and shared common/ 
COPY pv_rm_interface ./pv_rm_interface
COPY common ./common
COPY pyproject.toml uv.lock ./

# Install uv and sync project environment
RUN pip install --no-cache-dir uv
RUN uv sync --frozen --no-dev

# Run the command on container startup
CMD ["uv", "run", "python", "-m", "pv_rm_interface.main"]
