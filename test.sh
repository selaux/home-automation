#!/bin/sh

set -e

pylint --rcfile=.pylintrc gateway/*.py
pylint --rcfile=test/.pylintrc test/gateway/*.py
TEST_ENV=1 python -m unittest discover -s test/gateway -p 'test_*.py'
