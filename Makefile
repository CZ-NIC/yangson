PROJECT = yangson
VERSION = 1.3.15
.PHONY = tags deps install-deps test

tags:
	find $(PROJECT) -name "*.py" | etags -

deps:
	mv requirements.txt requirements.txt.old
	pip freeze > requirements.txt

install-deps:
	pip install -r requirements.txt

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
