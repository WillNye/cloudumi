# Celery Tasks

The true work horse of the backend, most tasks are scheduled tasks that recur periodically.

- To run locally: `bazel run //common/celery_tasks:bin`
- To run in a docker container: `bazel run //common/celery_tasks:container-dev-local` - has the benefit of running closer to how we deploy into production
