#!/bin/bash

echo "🚀 Запуск Tribute Webhook Server..."

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+"
    exit 1
fi

echo "🔄 Обновление из GitHub..."
git pull
echo "✅ Обновлено!"

# Установка зависимостей
if [ -f "requirements.txt" ]; then
    echo "📥 Установка зависимостей..."
    pip install --no-cache-dir -r requirements.txt
else
    echo "⚠️  requirements.txt не найден!"
fi

# Создание директорий
echo "📁 Создание необходимых директорий..."
mkdir -p logs
mkdir -p data

# Проверка config.yaml
if [ ! -f "config.yaml" ]; then
    echo "❌ config.yaml не найден! Создайте его из примера."
    exit 1
fi

# Запуск сервера
echo "✅ Запуск сервера..."
python3 main.py
