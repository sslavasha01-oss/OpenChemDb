# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем системные зависимости для RDKit и сборки
RUN apt-get update && apt-get install -y \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 chemist && \
    useradd -u 1000 -g chemist -m -s /bin/bash chemist

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY --chown=chemist:chemist ./app ./app

# Создаем пустую папку data (она будет перекрыта Volume)
RUN mkdir -p /app/data && chown chemist:chemist /app/data

USER chemist

# Команда запуска через uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]