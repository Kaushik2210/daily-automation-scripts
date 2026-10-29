.PHONY: lint test index check

lint:
	ruff check .

test:
	pytest scripts

index:
	python tools/update_index.py

check: lint test
