COMPOSE_APP_FILE := docker-compose-prod.yml
COMPOSE_INFRA_FILE := docker-compose-prod-infra.yml
# Твой файл для локальной разработки
COMPOSE_LOCAL_FILE := docker-compose.yml

.PHONY: up down restart update status logs wait_for_dbs prod-up prod-down prod-update local-update local-down

# Функция-помощник для проверки готовности баз данных принимать коннекты
wait_for_dbs:
	@echo "--- Ожидание полной готовности баз данных (users_db и archive_db) ---"
	@until docker exec users_db pg_isready -U chemist -d users_db > /dev/null 2>&1; do \
	   echo "Ждем users_db..."; \
	   sleep 2; \
	done
	@until docker exec archive_db pg_isready -U chemist -d archive_db > /dev/null 2>&1; do \
	   echo "Ждем archive_db (на 3 млн реакций)..."; \
	   sleep 2; \
	done
	@echo "--- Обе базы данных полностью готовы! ---"

# === ЛОКАЛЬНАЯ РАЗРАБОТКА (docker-compose.yml) ===

# Простой запуск локалки
up:
	@echo "--- Запуск локального окружения ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d

# Полное точечное обновление для локалки 1 в 1 как на проде
update:
	@echo "--- Пересборка локального фронтенда и апп без кэша ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) build --no-cache frontend-builder app
	@echo "--- Перезапуск контейнера сборщика фронта ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d --no-deps frontend-builder
	@echo "--- Перезапуск контейнера FastAPI (app) ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d --no-deps app
	@$(MAKE) wait_for_dbs
	@echo "--- Применение новых миграций Alembic локально ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) exec app alembic upgrade head
	@echo "--- Локальное обновление завершено! ---"

# Остановка локалки
down:
	@echo "--- Остановка локального окружения ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) down


# === ПРОДАКШН (docker-compose-prod.yml / docker-compose-prod-infra.yml) ===

# Полный запуск продакшена с нуля
prod-up:
	@echo "--- Запуск основного приложения (создание сети и баз) ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d
	@$(MAKE) wait_for_dbs
	@echo "--- Запуск миграций Alembic ---"
	docker compose -f $(COMPOSE_APP_FILE) exec app alembic upgrade head
	@echo "--- Запуск инфраструктурного стека (мониторинг, прокси) ---"
	docker compose -f $(COMPOSE_INFRA_FILE) up -d
	@echo "--- Все контейнеры успешно запущены и миграции применены! ---"

# Остановка продакшена
prod-down:
	@echo "--- Остановка инфраструктуры ---"
	docker compose -f $(COMPOSE_INFRA_FILE) down
	@echo "--- Остановка приложения ---"
	docker compose -f $(COMPOSE_APP_FILE) down

# ТОЧЕЧНОЕ ОБНОВЛЕНИЕ НА ПРОДЕ БЕЗ КЭША С МИГРАЦИЯМИ
prod-update:
	@echo "--- Пересборка фронтенда и апп без кэша ---"
	docker compose -f $(COMPOSE_APP_FILE) build --no-cache frontend-builder app
	@echo "--- Перезапуск контейнера сборщика фронта ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d --no-deps frontend-builder
	@echo "--- Перезапуск контейнера FastAPI (app) ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d --no-deps app
	@$(MAKE) wait_for_dbs
	@echo "--- Применение новых миграций Alembic ---"
	docker compose -f $(COMPOSE_APP_FILE) exec app alembic upgrade head
	@echo "--- Обновление завершено! Базы и инфра не прерывали аптайм. ---"