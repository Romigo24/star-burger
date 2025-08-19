#!/bin/bash
cd /opt/star-burger
git pull

echo "[deploy] Останавливаю контейнеры и очищаю статику..."
docker-compose -f docker-compose.prod.yaml down
sudo rm -rf /var/www/frontend/*
sudo mkdir -p /var/www/frontend
sudo chmod -R 755 /var/www/frontend

echo "[deploy] Собираю фронтенд..."
docker-compose -f docker-compose.prod.yaml up --build -d frontend
sleep 10

echo "[deploy] Запускаю backend и применяю миграции..."
docker-compose -f docker-compose.prod.yaml up --build -d backend db
sleep 5
docker-compose -f docker-compose.prod.yaml exec backend python manage.py migrate

echo "[deploy] Собираю статику Django..."
docker-compose -f docker-compose.prod.yaml exec backend python manage.py collectstatic --noinput

echo "[deploy] Перезапускаю nginx..."
sudo systemctl restart nginx