pytest := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest --ignore 'functional_tests' \
	-c pytest.ini . #--tb short \
	--cov-config .coveragerc --cov common --cov api \
	--async-test-timeout=1600 --timeout=1600 -n auto \
	--asyncio-mode=auto --dist loadscope \
    --ignore-glob 'bazel*' --ignore 'functional_tests'  .

pytest_functional := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest -c pytest.ini functional_tests

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

.PHONY: ecs-tunnel-staging-ssh
ecs-tunnel-staging-ssh:
	export AWS_PROFILE=staging/staging_admin
	@TASK_ID=$$(aws ecs list-tasks --cluster staging-noq-dev-shared-staging-1 --service api --profile staging/staging_admin --region us-west-2 --query 'taskArns[0]' --output text | awk -F/ '{print $$NF}') && \
	AWS_PROFILE=staging/staging_admin ecs-tunnel -L 2222:22 -c staging-noq-dev-shared-staging-1 -t $$TASK_ID --region us-west-2

.PHONY: ecs-tunnel-staging-celery-flower
ecs-tunnel-staging-celery-flower:
	export AWS_PROFILE=staging/staging_admin
	@TASK_ID=$$(aws ecs list-tasks --cluster staging-noq-dev-shared-staging-1 --service celery_flower --profile staging/staging_admin --region us-west-2 --query 'taskArns[0]' --output text | awk -F/ '{print $$NF}') && \
	AWS_PROFILE=staging/staging_admin ecs-tunnel -L 7101:7101 -c staging-noq-dev-shared-staging-1 -t $$TASK_ID --region us-west-2

.PHONY: ecs-tunnel-prod-celery-flower
ecs-tunnel-prod-celery-flower:
	export AWS_PROFILE=prod/prod_admin
	@TASK_ID=$$(aws ecs list-tasks --cluster noq-dev-shared-prod-1 --service celery_flower --profile prod/prod_admin --region us-west-2 --query 'taskArns[0]' --output text | awk -F/ '{print $$NF}') && \
	AWS_PROFILE=prod/prod_admin ecs-tunnel -L 7101:7101 -c noq-dev-shared-prod-1 -t $$TASK_ID --region us-west-2

.PHONY: ecsgo-staging
ecsgo-staging:
	@export AWS_DEFAULT_REGION=us-west-2 && \
	export AWS_REGION=us-west-2 && \
	export AWS_PROFILE=staging/staging_admin && \
	ecsgo --cluster staging-noq-dev-shared-staging-1 --region us-west-2

.PHONY: ecsgo-prod
ecsgo-prod:
	@export AWS_DEFAULT_REGION=us-west-2 && \
	export AWS_REGION=us-west-2 && \
	export AWS_PROFILE=prod/prod_admin && \
	ecsgo --cluster noq-dev-shared-prod-1 --region us-west-2
