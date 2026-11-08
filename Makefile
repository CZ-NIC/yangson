PROJECT = yangson
VERSION := $(shell uv version --short)
COMPLETIONS = completions/bash/yangson completions/zsh/_yangson \
	completions/fish/yangson.fish
.PHONY: all clean completions deps documentation install-deps lint test

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

completions: $(COMPLETIONS)

$(COMPLETIONS): yangson/cli.py
	uv run --group dev tools/python/generate_completions.py

documentation:
	$(MAKE) -C docs html man

release:
	git tag -a -s -m "Yangson release $(VERSION)" $(VERSION)
	git push --follow-tags
	uv build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .ropeproject
