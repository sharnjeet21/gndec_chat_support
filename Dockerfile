FROM python:3.13.5-slim

# -------------------------------
# System setup
# -------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# Python dependencies
# -------------------------------
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# -------------------------------
# Application code
# -------------------------------
COPY backend ./backend
COPY data ./data

# -------------------------------
# Pre-build vector store
# -------------------------------
RUN python3 backend/build_vector_db.py

# -------------------------------
# Runtime
# -------------------------------
EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]

