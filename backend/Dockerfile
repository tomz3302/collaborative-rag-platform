# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the reranker model so it's baked into the image
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')"

# Copy the entire backend application
COPY . .


# Expose port 8000 (FastAPI default)
EXPOSE 8000

# Command to run the application
# Using uvicorn to run the FastAPI app
CMD ["uvicorn", "rag_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
