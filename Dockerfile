FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости системы для сборки пакетов, если понадобится
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Приложение слушает порт 8000
EXPOSE 8000

CMD ["python", "main.py"]
