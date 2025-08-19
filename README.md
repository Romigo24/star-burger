# Сайт доставки еды Star Burger

[![Demo Version](https://img.shields.io/badge/демо--версия_сайта-%E2%86%92_Star_Burger-blue)](https://e-example.ru)

Это сайт сети ресторанов Star Burger. Здесь можно заказать превосходные бургеры с доставкой на дом.

![Скриншот сайта](https://dvmn.org/filer/canonical/1594651635/686/)

Сеть Star Burger объединяет несколько ресторанов, действующих под единой франшизой. У всех ресторанов одинаковое меню и одинаковые цены. Просто выберите блюдо из меню на сайте и укажите место доставки. Мы сами найдём ближайший к вам ресторан, всё приготовим и привезём.

На сайте есть три независимых интерфейса. Первый — это публичная часть, где можно выбрать блюда из меню и быстро оформить заказ без регистрации и SMS. Второй интерфейс предназначен для менеджера: здесь происходит обработка заказов. Менеджер подтверждает заказы, выбирает ближайший ресторан и передаёт заказ на исполнение. Третий интерфейс — админка, используемая программистами для разработки и менеджером для обновления меню.



## Подготовка сервера
Перед деплоем выполните следующие шаги:

1. **Установите зависимости**:
   - Docker и Docker Compose.
   - Nginx (настройте самостоятельно, см. ниже).
   - Certbot для HTTPS (настройте самостоятельно, см. ниже).

2. **Создайте необходимые папки**:
   - Создайте директории для статики и медиа на сервере:
     ```sh
     sudo mkdir -p /var/www/frontend
     sudo mkdir -p /var/www/media
     sudo chmod -R 755 /var/www/frontend /var/www/media
     ```

3. **Настройте Nginx:**
   - Установите Nginx: `sudo apt install nginx`.
   - Создайте конфигурационный файл (например, `/etc/nginx/sites-available/star-burger`):

```nginx
server {
    server_name your-domain.ru;

    location /static/ {
        alias /var/www/frontend/;
        access_log off;
        expires 30d;
    }

    location /media/ {
        alias /var/www/media/;
        access_log off;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

   - Активируйте конфиг: `sudo ln -s /etc/nginx/sites-available/star-burger /etc/nginx/sites-enabled/`.
   - Проверьте и перезапустите: `sudo nginx -t && sudo systemctl restart nginx`.

4. **Настройте HTTPS с Certbot:**
   - Установите Certbot: `sudo apt install certbot python3-certbot-nginx`.
   - Получите сертификат: `sudo certbot --nginx -d your-domain.com -m your-email@example.com --agree-tos --non-interactive`.
   - Настройте редирект HTTP → HTTPS в конфиге Nginx при необходимости.

# Быстрый старт (локально)

1. Клонируйте репозиторий и перейдите в папку проекта:
   ```sh
   git clone https://github.com/Romigo24/star-burger.git
   cd star-burger
   ```
2. Создайте файл `.env` в папке backend/ со следующим содержимым:
   ```env
   SECRET_KEY=django-insecure-0if40nf4nf93n4
   YANDEX_GEOCODER_API_KEY=ваш_ключ_от_яндекса
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   DATABASE_URL=postgres://user:password@localhost:5432/dbname
   ```
3. Запустите проект:
   ```sh
   docker-compose up --build
   ```

# Структура проекта

- backend/ — Django-проект (manage.py, requirements.txt, приложения, статика, медиа, шаблоны, Dockerfile)
- frontend/ — фронтенд (package.json, исходники, ассеты, node_modules, bundles, Dockerfile)
- docker-compose.yaml, docker-compose.prod.yaml, deploy.sh — в корне


# Деплой на сервер

1. Установите Docker, Docker Compose, Nginx, Certbot.
2. Создайте папки для статики и медиа:
   ```sh
   sudo mkdir -p /var/www/frontend /var/www/media
   sudo chmod -R 755 /var/www/frontend /var/www/media
   ```
3. Настройте Nginx (см. пример конфига выше).
4. Создайте файл `.env` в папке backend/ на сервере:
   ```env
   SECRET_KEY=django-insecure-0if40nf4nf93n4
   YANDEX_GEOCODER_API_KEY=ваш_ключ_от_яндекса
   DEBUG=False
   ALLOWED_HOSTS=your-domain.com
   DATABASE_URL=postgres://user:password@db:5432/dbname
   ROLLBAR_ACCESS_TOKEN=ваш_токен_rollbar
   ```
5. Выполните деплой:
   ```sh
   ./deploy.sh
   ```

# Как это работает
- Все данные и media-файлы сохраняются благодаря volumes.
- Статика и фронт собираются внутри контейнеров и автоматически попадают в нужные папки.
- После перезапуска или пересоздания контейнеров данные не теряются.

## Мониторинг ошибок
Интеграция с Rollbar позволяет:
- Отслеживать ошибки в реальном времени.
- Просматривать историю деплоев.
- Связывать ошибки с версиями кода.

Настройте `ROLLBAR_ACCESS_TOKEN` в `.env` для активации.

## Цели проекта
Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте Devman. За основу взят код проекта FoodCart.
