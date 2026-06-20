# Переменные для удобства
COMPOSE_APP_FILE := docker-compose-prod.yml
COMPOSE_INFRA_FILE := docker-compose-prod-infra.yml

.PHONY: up down restart update status logs ps

# 1. Полный запуск всего стека с нуля (в правильном порядке)
up:
	@echo "--- Запуск основного приложения (создание сети и баз) ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d
	@echo "--- Ожидание инициализации сети... ---"
	@sleep 2
	@echo "--- Запуск инфраструктурного стека (мониторинг, прокси) ---"
	docker compose -f $(COMPOSE_INFRA_FILE) up -d
	@echo "--- Все контейнеры успешно запущены! ---"

# 2. Остановка всех контейнеров
down:
	@echo "--- Остановка инфраструктуры ---"
	docker compose -f $(COMPOSE_INFRA_FILE) down
	@echo "--- Остановка приложения ---"
	docker compose -f $(COMPOSE_APP_FILE) down

# 3. Полный перезапуск без пересборки
restart: down up

# 4. УМНОЕ ОБНОВЛЕНИЕ ПРИЛОЖЕНИЯ И ФРОНТЕНДА (--no-cache)
# Пересобирает только app и frontend-builder без кэша, остальные контейнеры просто перезапускает при необходимости
update:
	@echo "--- Пересборка frontend-builder и app без кэша ---"
	docker compose -f $(COMPOSE_APP_FILE) build --no-cache frontend-builder app
	@echo "--- Перезапуск обновленного приложения ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d --no-deps frontend-builder app
	@echo "--- Проверка и поднятие остального стека приложения ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d
	@echo "--- Синхронизация инфраструктурного стека ---"
	docker compose -f $(COMPOSE_INFRA_FILE) up -d
	@echo "--- Обновление завершено! ---"