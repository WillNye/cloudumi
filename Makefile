pytest := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest --ignore 'functional_tests' -c pytest.ini . #--tb short \
	--cov-config .coveragerc --cov common --cov api \
	--async-test-timeout=1600 --timeout=1600 -n auto \
	--asyncio-mode=auto --dist loadscope \
    --ignore-glob 'bazel*' --ignore 'functional_tests'  .

pytest_functional := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest -c pytest.ini .

pytest_single_process := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(pwd) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest --tb short \
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

.PHONY: functional_test
functional_test: clean
	ASYNC_TEST_TIMEOUT=1600 $(pytest_functional)

.PHONY: testhtml
testhtml: clean
	ASYNC_TEST_TIMEOUT=1600 $(pytest) $(html_report) && echo "View coverage results in htmlcov/index.html"

.PHONY: test-lint
test-lint: test lint

.PHONY: docker_build
docker_build:
	 docker buildx build --platform=linux/amd64 .

.PHONY: docker_up
docker_up:
	noq file -p arn:aws:iam::759357822767:role/NoqSaasRoleLocalDev  arn:aws:iam::759357822767:role/NoqSaasRoleLocalDev -f
	docker-compose -f docker-compose.yaml -f deploy/docker-compose-dependencies.yaml up -d

.PHONY: docker_down
docker_down:
	docker-compose -f docker-compose.yaml -f deploy/docker-compose-dependencies.yaml down

.PHONY: docker_deps_up
docker_deps_up:
	docker-compose -f deploy/docker-compose-dependencies.yaml up -d

.PHONY: docker_deps_down
docker_deps_down:
	docker-compose -f deploy/docker-compose-dependencies.yaml down

.PHONY: ssm_prod
ssm_prod:
	AWS_REGION=us-west-2 AWS_DEFAULT_REGION=us-west-2 AWS_PROFILE=prod/prod_admin ecsgo

.PHONY: ssm_staging
ssm_staging:
	AWS_REGION=us-west-2 AWS_DEFAULT_REGION=us-west-2 AWS_PROFILE=staging/staging_admin ecsgo
