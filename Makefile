PROJECT = yangson
VERSION := $(shell uv version --short)
.PHONY: all build clean completions deps documentation install-deps lint release test

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

completions:
	uv run --group dev tools/python/generate_completions.py

documentation:
	uv run --group docs $(MAKE) -C docs html man

build: completions documentation
	uv build

release: build
	git tag -a -s -m "Yangson release $(VERSION)" $(VERSION)
	git push --follow-tags

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .ropeproject
