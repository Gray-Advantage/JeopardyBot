run:
	python main.py

ruff:
	ruff check .

mypy:
	mypy .

lint: ruff mypy