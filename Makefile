.PHONY: dev test build up down logs

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f worker

test:
	python -m pytest tests/ -v

build:
	docker build -t wearon-worker .
