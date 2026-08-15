# -------------------------------
# Stage 1: Build React Frontend
# -------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/support_ui
COPY support_ui/package*.json ./
RUN npm install
COPY support_ui/ ./
RUN npm run build

# -------------------------------
# Stage 2: Python Backend Runtime
# -------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

RUN pip install --no-cache-dir python-multipart groq

# Copy application code
COPY backend ./backend
COPY data ./data

# Copy pre-built React frontend static assets from Stage 1
COPY --from=frontend-builder /app/support_ui/dist ./support_ui/dist

# Expose backend server port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
