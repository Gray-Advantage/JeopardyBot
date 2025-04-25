migrations:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

db: migrate migrations migrate

dumpdata:
	python -m app.fixtures.fixtures dump ./app/fixtures/data.json

loaddata:
	python -m app.fixtures.fixtures load ./app/fixtures/data.json

down:
	docker compose down

up:
	docker compose up --build -d

reset: down up migrate loaddata

ruff:
	ruff check .

mypy:
	mypy .

lint: ruff mypy