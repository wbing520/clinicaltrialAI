.PHONY: dev test fmt

dev:
	@echo "Create venv and install via Poetry (run locally): poetry install"

fmt:
	black src tests

test:
	pytest -q
