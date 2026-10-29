PROJECT = yangson
VERSION := $(shell uv version --short)
.PHONY = tags deps install-deps test

deps:
	@uv lock

install-deps:
	@uv sync --all-groups

test:
	@uv run --all-groups pytest tests

release:
	git tag -a -s -m "Yangson release $(VERSION)" $(VERSION)
	git push --follow-tags
	uv build
