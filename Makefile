.PHONY: dev test build up down logs prod-up prod-down prod-logs prod-pull

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

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

prod-pull:
	docker compose -f docker-compose.prod.yml pull
