PYTHON = python3.7

all: ve/bin/zope-testrunner

ve:
	set -e; \
	  $(PYTHON) -m venv ve; \
	  ve/bin/pip install --upgrade setuptools; \
	  ve/bin/pip install --upgrade wheel

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

.PHONY: lint
lint:
	ve/bin/flake8 ./src/

clean:
	rm -rf ve .tox .coverage coverage.xml
