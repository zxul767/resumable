.PHONY: install demo test lint format typecheck check clean

UV_CACHE_DIR ?= /tmp/uv-cache
UV = UV_CACHE_DIR=$(UV_CACHE_DIR) uv

install:
	$(UV) sync --dev

demo:
	$(UV) run python -m resumable.demo

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check --fix .

format:
	$(UV) run ruff format .

typecheck:
	$(UV) run pyright

check: lint typecheck test

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache
