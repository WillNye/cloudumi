pytest := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	pytest --tb short \
	--cov-config .coveragerc --cov common --cov api \
	--async-test-timeout=300 --timeout=300 -n auto \
	--asyncio-mode=auto --dist loadscope \
    --ignore-glob 'bazel*' .

html_report := --cov-report html
test_args := --cov-report term-missing

.PHONY: clean
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -f celerybeat-schedule.db
	rm -f celerybeat-schedule
	rm -rf consoleme.tar.gz
	rm -rf ui/.npmrc ui/.yarnrc
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*.egg-link' -delete

.PHONY: test
test: clean
	ASYNC_TEST_TIMEOUT=60 $(pytest)

.PHONY: testhtml
testhtml: clean
	ASYNC_TEST_TIMEOUT=60 $(pytest) $(html_report) && echo "View coverage results in htmlcov/index.html"

.PHONY: test-lint
test-lint: test lint