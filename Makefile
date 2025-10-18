POETRY ?= poetry
DOCKER_COMPOSE ?= docker-compose

.PHONY: setup lint typecheck test format up down logs loadtest

setup:
$(POETRY) install --no-root

lint:
$(POETRY) run ruff check src tests

format:
$(POETRY) run ruff format src tests

typecheck:
$(POETRY) run mypy --config-file pyproject.toml src

test:
$(POETRY) run pytest --cov=genesis --cov-report=term-missing

up:
$(DOCKER_COMPOSE) up --build -d

logs:
$(DOCKER_COMPOSE) logs -f

down:
$(DOCKER_COMPOSE) down -v

loadtest:
cd scripts && k6 run loadtest.js
