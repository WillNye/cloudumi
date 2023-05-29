pytest := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest --ignore 'functional_tests' \
	--tb short \
	--cov-config .coveragerc --cov common --cov api \
	--async-test-timeout=1600 --timeout=1600 -n auto \
	--asyncio-mode=auto --dist loadscope \
    --ignore-glob 'bazel*' --ignore 'functional_tests'  .

pytest_functional := PYTHONDONTWRITEBYTECODE=1 \
	PYTEST_PLUGINS=util.tests.fixtures.fixtures \
	PYTHONPATH=$(PWD) \
	AWS_DEFAULT_REGION=us-east-1 \
	CONFIG_LOCATION=util/tests/test_configuration.yaml \
	python -m pytest functional_tests

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

BASE_DIR := $(shell pwd)
AWS_PROFILE_STAGING = staging/staging_admin
AWS_REGION_STAGING = us-west-2
STAGING_VAR_FILES = --var-file=live/shared/staging-1/noq.dev-staging.tfvars --var-file=live/shared/staging-1/secret.tfvars

AWS_PROFILE_PROD = production/prod_admin
AWS_REGION_PROD = us-west-2
PROD_VAR_FILES = --var-file=live/shared/prod-1/noq.dev-prod.tfvars --var-file=live/shared/prod-1/secret.tfvars

.PHONY: tf-staging-refresh tf-staging-plan tf-staging-apply tf-prod-refresh tf-prod-plan tf-prod-apply

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

.PHONY: docker_clean
docker_clean:
	docker-compose -f deploy/docker-compose-dependencies.yaml down -v
	@containers=$$(docker ps -aq --filter "name=.*cloudumi.*"); \
	if [ -z "$$containers" ]; then \
		echo "No CloudUmi Docker Containers to Delete"; \
	else \
		docker rm $$containers; \
	fi
	@volumes=$$(docker volume ls -q --filter "name=.*cloudumi.*"); \
    if [ -z "$$volumes" ]; then \
        echo "No CloudUmi Docker Volumes to Delete"; \
    else \
        docker volume rm $$volumes; \
    fi

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
	docker-compose -f deploy/docker-compose-dependencies.yaml up -d --force-recreate

.PHONY: docker_deps_down
docker_deps_down:
	docker-compose -f deploy/docker-compose-dependencies.yaml down

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

.PHONY: ecs-set-ssh-password-staging
ecs-set-ssh-password-staging:
	@TASK_ID=$$(aws ecs list-tasks --cluster staging-noq-dev-shared-staging-1 --service api --profile staging/staging_admin --region us-west-2 --query 'taskArns[0]' --output text | awk -F/ '{print $$NF}') && \
	CONTAINER_NAME=$$(aws ecs describe-tasks --tasks $$TASK_ID --cluster staging-noq-dev-shared-staging-1 --profile staging/staging_admin --region us-west-2 --query 'tasks[0].containers[0].name' --output text) && \
	aws ecs execute-command --cluster staging-noq-dev-shared-staging-1 --task $$TASK_ID --container $$CONTAINER_NAME --command "/bin/sh -c 'echo root:TEMP_PASS | chpasswd'" --profile staging/staging_admin --region us-west-2 --interactive

.PHONY: ecs-tunnel-staging-ssh
ecs-tunnel-staging-ssh: ecs-set-ssh-password-staging
	@echo "SSH to the staging host with the following command:"
	@echo "ssh root@127.0.0.1 -p 2222"
	@echo "Password: TEMP_PASS"
	export AWS_PROFILE=staging/staging_admin
	@TASK_ID=$$(aws ecs list-tasks --cluster staging-noq-dev-shared-staging-1 --service api --profile staging/staging_admin --region us-west-2 --query 'taskArns[0]' --output text | awk -F/ '{print $$NF}') && \
	AWS_PROFILE=staging/staging_admin ecs-tunnel -L 2222:22 -c staging-noq-dev-shared-staging-1 -t $$TASK_ID --region us-west-2

.PHONY: ecs-set-ssh-password-prod
ecs-set-ssh-password-prod:
	@TASK_ID=$$(aws ecs list-tasks --cluster noq-dev-shared-prod-1 --service api --profile prod/prod_admin --region us-west-2 --query 'taskArns[0]' --output text | awk -F/ '{print $$NF}') && \
	CONTAINER_NAME=$$(aws ecs describe-tasks --tasks $$TASK_ID --cluster noq-dev-shared-prod-1 --profile prod/prod_admin --region us-west-2 --query 'tasks[0].containers[0].name' --output text) && \
	aws ecs execute-command --cluster noq-dev-shared-prod-1 --task $$TASK_ID --container $$CONTAINER_NAME --command "/bin/sh -c 'echo root:TEMP_PASS | chpasswd'" --profile prod/prod_admin --region us-west-2 --interactive

tf-staging-refresh:
	@cd deploy/infrastructure && \
	export AWS_PROFILE=$(AWS_PROFILE_STAGING) AWS_REGION=$(AWS_REGION_STAGING); \
	terraform workspace select shared-staging-1; \
	terraform refresh $(STAGING_VAR_FILES)

tf-staging-plan:
	@cd deploy/infrastructure && \
	export AWS_PROFILE=$(AWS_PROFILE_STAGING) AWS_REGION=$(AWS_REGION_STAGING); \
	terraform workspace select shared-staging-1; \
	terraform plan $(STAGING_VAR_FILES)

tf-staging-apply:
	@cd deploy/infrastructure && \
	export AWS_PROFILE=$(AWS_PROFILE_STAGING) AWS_REGION=$(AWS_REGION_STAGING); \
	terraform workspace select shared-staging-1; \
	terraform apply $(STAGING_VAR_FILES)

tf-prod-refresh:
	@cd deploy/infrastructure && \
	export AWS_PROFILE=$(AWS_PROFILE_PROD) AWS_REGION=$(AWS_REGION_PROD); \
	terraform workspace select shared-prod-1; \
	terraform refresh $(PROD_VAR_FILES)

tf-prod-plan:
	@cd deploy/infrastructure && \
	export AWS_PROFILE=$(AWS_PROFILE_PROD) AWS_REGION=$(AWS_REGION_PROD); \
	terraform workspace select shared-prod-1; \
	terraform plan $(PROD_VAR_FILES)

tf-prod-apply:
	@cd deploy/infrastructure && \
	export AWS_PROFILE=$(AWS_PROFILE_PROD) AWS_REGION=$(AWS_REGION_PROD); \
	terraform workspace select shared-prod-1; \
	terraform apply $(PROD_VAR_FILES)

.PHONY: deploy-staging
deploy-staging:
	@./deploy/infrastructure/live/shared/staging-1/push_all_the_things.sh

.PHONY: deploy-prod
deploy-prod:
	@./deploy/infrastructure/live/shared/prod-1/push_all_the_things.sh

.PHONY: update-config-staging
update-config-staging:
	@echo "Updating SaaS configuration for staging environment..."
	@cd deploy/infrastructure && \
	terraform workspace select shared-staging-1 && \
	terraform output -json | python ../../util/terraform_config_parser/terraform_config_parser.py $(BASE_DIR)
	@echo "SaaS configuration for staging environment updated."

.PHONY: update-config-prod
update-config-prod:
	@echo "Updating SaaS configuration for production environment..."
	@cd deploy/infrastructure && \
	terraform workspace select shared-prod-1 && \
	terraform output -json | python ../../util/terraform_config_parser/terraform_config_parser.py $(BASE_DIR)
	@echo "SaaS configuration for production environment updated."

.PHONY: generate_pydantic_models_from_swagger_spec
generate_pydantic_models_from_swagger_spec:
	@echo "Generating pydantic models from swagger spec..."
	@cd common/util && \
	datamodel-codegen --input swagger.yaml  --output ../models.py --base-class common.lib.pydantic.BaseModel --field-extra-keys 'is_secret' && \
	black ../models.py
	@echo "Pydantic models generated."