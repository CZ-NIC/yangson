PROJECT = yangson
VERSION := $(shell uv version --short)
.PHONY = all clean deps install-deps lint test

all: lint test

deps:
	@uv lock

install-deps:
	@uv sync --all-groups

test:
	@uv run --all-groups pytest tests

lint:
	@echo "===== Linting ====="
	@uv run ruff check .

release:
	git tag -a -s -m "Yangson release $(VERSION)" $(VERSION)
	git push --follow-tags
	uv build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .ropeproject
