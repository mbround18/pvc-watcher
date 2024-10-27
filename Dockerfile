# Dockerfile for PVC Scaler Application

# Base image with Python
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the pdm project metadata
COPY pyproject.toml pdm.lock README.md /app/

# Install PDM
RUN pip install pdm && pdm install --production

# Copy the source code
COPY src /app/src

# Set the command to run the PVC scaler script
CMD ["pdm", "run", "kopf", "run", "src/pvc_watcher/pvc_scaler.py"]
