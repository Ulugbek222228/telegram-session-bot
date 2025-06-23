# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Делаем папку внутри контейнера
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Запускаем main.py
CMD ["python", "main.py"]
