PROJECT = yangson
VERSION = 1.3.62
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
	rm -f dist/*
	python setup.py sdist
	python setup.py bdist_wheel

upload:
	twine upload dist/*
