PROJECT = yangson
VERSION := $(shell grep '^version' pyproject.toml | cut -d'"' -f2)
.PHONY = tags deps install-deps test

tags:
	find $(PROJECT) -name "*.py" | etags -

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
