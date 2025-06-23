# Используем стабильный Python 3.11, т.к. в 3.13 нет imghdr
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё остальное
COPY . .

# Запуск бота
CMD ["python", "main.py"]
