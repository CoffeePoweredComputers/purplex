# =====================================================================================
# PURPLEX MAKEFILE
# =====================================================================================
# Common commands for development and deployment
# =====================================================================================

.PHONY: help
help: ## Show this help message
	@echo "Purplex Development & Deployment Commands"
	@echo "========================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =====================================================================================
# DEVELOPMENT COMMANDS
# =====================================================================================

.PHONY: dev
dev: ## Start development environment
	./start.sh

.PHONY: stop
stop: ## Stop development environment
	./stop.sh

.PHONY: install
install: ## Install all dependencies
	pip install -r requirements/development.txt
	cd purplex/client && yarn install

.PHONY: migrate
migrate: ## Run database migrations
	python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Create new migrations
	python manage.py makemigrations

.PHONY: shell
shell: ## Open Django shell
	python manage.py shell

.PHONY: dbshell
dbshell: ## Open database shell
	python manage.py dbshell

.PHONY: createsuperuser
createsuperuser: ## Create superuser account
	python manage.py createsuperuser

.PHONY: populate
populate: ## Populate sample data
	python manage.py populate_comprehensive

# =====================================================================================
# TESTING COMMANDS
# =====================================================================================

.PHONY: test
test: ## Run all tests
	pytest

.PHONY: test-unit
test-unit: ## Run unit tests only
	pytest -m unit

.PHONY: test-integration
test-integration: ## Run integration tests only
	pytest -m integration

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	pytest --cov=purplex --cov-report=html --cov-report=term

.PHONY: lint
lint: ## Run linters
	flake8 purplex/
	cd purplex/client && yarn lint

.PHONY: format
format: ## Format code
	black purplex/
	isort purplex/

.PHONY: typecheck
typecheck: ## Run type checking
	mypy purplex/
	cd purplex/client && yarn typecheck

# =====================================================================================
# BUILD COMMANDS
# =====================================================================================

.PHONY: build
build: ## Build production Docker images
	docker build -t purplex-app:latest .
	docker build -f Dockerfile.celery -t purplex-celery:latest .

.PHONY: build-frontend
build-frontend: ## Build frontend for production
	cd purplex/client && yarn build

.PHONY: collectstatic
collectstatic: ## Collect static files
	python manage.py collectstatic --noinput

# =====================================================================================
# DOCKER COMMANDS
# =====================================================================================

.PHONY: docker-up
docker-up: ## Start Docker services
	docker-compose -f config/docker/development.yml up -d

.PHONY: docker-down
docker-down: ## Stop Docker services
	docker-compose -f config/docker/development.yml down

.PHONY: docker-logs
docker-logs: ## View Docker logs
	docker-compose -f config/docker/development.yml logs -f

.PHONY: docker-clean
docker-clean: ## Clean Docker resources
	docker-compose -f config/docker/development.yml down -v
	docker system prune -f

# =====================================================================================
# PRODUCTION COMMANDS
# =====================================================================================

.PHONY: prod-build
prod-build: ## Build for production
	docker build -t purplex-app:prod .
	docker build -f Dockerfile.celery -t purplex-celery:prod .

.PHONY: prod-up
prod-up: ## Start production services
	docker-compose -f config/docker/production.yml up -d

.PHONY: prod-down
prod-down: ## Stop production services
	docker-compose -f config/docker/production.yml down

.PHONY: prod-deploy
prod-deploy: ## Deploy to production
	./deploy/scripts/deploy_to_aws.sh

# =====================================================================================
# DATABASE COMMANDS
# =====================================================================================

.PHONY: db-backup
db-backup: ## Backup database
	pg_dump -h localhost -U purplex_user -d purplex > backup_$(shell date +%Y%m%d_%H%M%S).sql

.PHONY: db-restore
db-restore: ## Restore database from backup
	@echo "Usage: make db-restore FILE=backup_20240101_120000.sql"
	psql -h localhost -U purplex_user -d purplex < $(FILE)

.PHONY: db-reset
db-reset: ## Reset database (WARNING: Deletes all data!)
	python manage.py flush --noinput
	python manage.py migrate
	python manage.py populate_comprehensive

# =====================================================================================
# UTILITY COMMANDS
# =====================================================================================

.PHONY: clean
clean: ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf purplex/client/dist/

.PHONY: requirements
requirements: ## Update requirements files
	pip freeze > requirements/current.txt
	@echo "Current requirements saved to requirements/current.txt"
	@echo "Review and update base.txt, development.txt, and production.txt as needed"

.PHONY: check-security
check-security: ## Check for security vulnerabilities
	safety check
	bandit -r purplex/

.PHONY: version
version: ## Show version
	@cat VERSION

.PHONY: bump-version
bump-version: ## Bump version number
	@echo "Current version: $$(cat VERSION)"
	@read -p "New version: " version; echo $$version > VERSION