FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/reviews_service /app/services/reviews_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.reviews_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
