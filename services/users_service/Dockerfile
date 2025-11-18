FROM python:3.13-slim

# Set working directory in the container
WORKDIR /app

# Prevent Python from writing .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the users service code
COPY services/users_service /app/services/users_service

# Ensure Python can import "services.users_service..."
ENV PYTHONPATH=/app

# Run the FastAPI app
CMD ["uvicorn", "services.users_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
