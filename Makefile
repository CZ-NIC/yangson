PROJECT = yangson
VERSION := $(shell grep '^version' pyproject.toml | cut -d'"' -f2)
.PHONY = tags deps install-deps test

tags:
	find $(PROJECT) -name "*.py" | etags -

deps:
	@pip-compile

install-deps:
	@pip-sync

test:
	@py.test tests

release:
	git tag -a -s -m "Yangson release $(VERSION)" $(VERSION)
	git push --follow-tags
	poetry build

type-check:
	@mypy
