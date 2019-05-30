PYTHON = python3

all: ve/bin/zope-testrunner

ve:
	virtualenv -p $(PYTHON) ve
	ve/bin/pip install -e .[test]

ve/bin/zope-testrunner: | ve
	ve/bin/pip install zope.testrunner

.PHONY: test
test: ve/bin/zope-testrunner
	ve/bin/zope-testrunner -vpc1 --all --test-path=${PWD}/src

test-coverage: ve/bin/zope-testrunner
	ve/bin/coverage erase
	ve/bin/coverage run ve/bin/zope-testrunner -vpc1 --all --test-path=${PWD}/src
	ve/bin/coverage report -m --include="src/shoobx/immutable/*" --omit="test*"

clean:
	rm -rf ve .tox .coverage coverage.xml
