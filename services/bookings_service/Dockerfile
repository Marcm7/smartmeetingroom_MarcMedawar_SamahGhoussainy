FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/bookings_service /app/services/bookings_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.bookings_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
