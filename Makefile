run:
	python main.py

migrations:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

ruff:
	ruff check .

mypy:
	mypy .

lint: ruff mypy