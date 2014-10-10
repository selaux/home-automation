#!/bin/sh

set -e

pylint --rcfile=.pylintrc gateway/*.py
pylint --rcfile=test/.pylintrc test/gateway/*.py
TEST_ENV=1 coverage run -m unittest discover -s test/gateway -p 'test_*.py'
coverage report --fail-under 95
