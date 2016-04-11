PROJECT = yangson
.PHONY = tags deps install-deps test

tags:
	find $(PROJECT) -name "*.py" | etags -

deps:
	pip freeze > requirements.txt

install-deps:
	pip install -r requirements.txt

test:
	@py.test tests
