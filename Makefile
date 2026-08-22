COMPOSE_APP_FILE := docker-compose-prod.yml
COMPOSE_INFRA_FILE := docker-compose-prod-infra.yml
COMPOSE_LOCAL_FILE := docker-compose.yml

.PHONY: up down restart update status logs prod-up prod-down prod-update local-update local-down

# === LOCAL DEVELOPMENT ===

# Шаг 1: Фоновый запуск только БД для распаковки и инициализации дампа
init-db:
	@echo "--- Starting database containers for initialization ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d users_db archive_db
	@echo "--- Databases started! Check logs via 'docker compose logs -f archive_db' to see progress. ---"

# Автоматизированный первый запуск (после того как archive_db готова)
first-start: up update
	@echo "--- First-time setup completed successfully! ---"

up:
	@echo "--- Starting local environment ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d

update:
	@echo "--- Rebuilding local frontend and app without cache ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) build --no-cache frontend-builder app
	@echo "--- Running frontend builder ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d --no-deps frontend-builder
	@echo "--- Restarting app container and waiting for healthchecks ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) up -d --no-deps --wait app
	@echo "--- Running Alembic migrations locally ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) exec app alembic upgrade head
	@echo "--- Local update completed! ---"

down:
	@echo "--- Stopping local environment ---"
	docker compose -f $(COMPOSE_LOCAL_FILE) down


# === PRODUCTION ===

prod-up:
	@echo "--- Starting PROD application ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d --wait app users_db archive_db scheduler
	@echo "--- Running Alembic migrations on PROD ---"
	docker compose -f $(COMPOSE_APP_FILE) exec app alembic upgrade head
	@echo "--- Starting PROD infrastructure ---"
	docker compose -f $(COMPOSE_INFRA_FILE) up -d
	@echo "--- PROD stack is fully up! ---"

prod-down:
	@echo "--- Stopping PROD infrastructure and app ---"
	docker compose -f $(COMPOSE_INFRA_FILE) down
	docker compose -f $(COMPOSE_APP_FILE) down

prod-update:
	@echo "--- Rebuilding PROD frontend and app without cache ---"
	docker compose -f $(COMPOSE_APP_FILE) build --no-cache frontend-builder app
	@echo "--- Running frontend builder ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d --no-deps frontend-builder
	@echo "--- Restarting app container and waiting for healthchecks ---"
	docker compose -f $(COMPOSE_APP_FILE) up -d --no-deps --wait app
	@echo "--- Running Alembic migrations on PROD ---"
	docker compose -f $(COMPOSE_APP_FILE) exec app alembic upgrade head
	@echo "--- PROD update completed! ---"
