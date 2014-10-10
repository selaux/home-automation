#!/bin/sh

pylint --rcfile=.pylintrc gateway/*.py
pylint --rcfile=test/.pylintrc test/gateway/*.py
python -m unittest discover -s test/gateway -p 'test_*.py'
