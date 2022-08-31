pytest := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	pytest --tb short \
	--cov-config .coveragerc --cov common --cov api \
	--async-test-timeout=1600 --timeout=1600 -n auto \
	--asyncio-mode=auto --dist loadscope \
    --ignore-glob 'bazel*' --ignore 'functional_tests'  .

pytest_single_process := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(pwd) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	pytest --tb short \
	--cov-config .coveragerc --cov common --cov api \
	--async-test-timeout=1600 --timeout=1600 \
	--asyncio-mode=auto \
    --ignore-glob 'bazel*' --ignore 'functional_tests' .

html_report := --cov-report html
test_args := --cov-report term-missing

.PHONY: clean
clean:
	rm -rf dist/ || echo $?
	rm -rf build/ || echo $?
	rm -rf *.egg-info || echo $?
	rm -rf .eggs/ || echo $?
	rm -rf .pytest_cache/ || echo $?
	rm -f celerybeat-schedule.db || echo $?
	rm -f celerybeat-schedule || echo $?
	rm -rf ui/.npmrc ui/.yarnrc || echo $?
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*.egg-link' -delete

.PHONY: test
test: clean
	ASYNC_TEST_TIMEOUT=1600 $(pytest)

.PHONY: testhtml
testhtml: clean
	ASYNC_TEST_TIMEOUT=1600 $(pytest) $(html_report) && echo "View coverage results in htmlcov/index.html"

.PHONY: test-lint
test-lint: test lint
