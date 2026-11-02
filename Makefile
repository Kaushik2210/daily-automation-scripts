.PHONY: lint test index check tools web

lint:
	ruff check .

test:
	pytest scripts

index:
	python tools/update_index.py

check: lint test

tools:
	python web/run_examples.py

web:
	python web/dashboard.py
