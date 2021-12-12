from collections import namedtuple

from pkg_resources import Distribution, EntryPoint, WorkingSet, load_entry_point

from util.log import logger

Plugin = namedtuple("Plugin", "Name ModulePath Attr")

cloudumi_plugins = [
    Plugin("cmsaas_metrics", "plugins.metrics.metrics", "Metric"),
    Plugin("cmsaas_config", "plugins.config.config", "Config"),
    Plugin("cmsaas_auth", "plugins.auth.auth", "Auth"),
    Plugin("cmsaas_aws", "plugins.aws.aws", "Aws"),
    Plugin(
        "cmsaas_celery_tasks", "plugins.celery_tasks.celery_tasks", "internal_schedule"
    ),
    Plugin(
        "cmsaas_celery_tasks_functions",
        "plugins.celery_tasks.celery_tasks",
        "CeleryTasks",
    ),
    Plugin("cmsaas_policies", "plugins.policies.policies", "Policies"),
    Plugin(
        "cmsaas_group_mapping", "plugins.group_mapping.group_mapping", "GroupMapping"
    ),
    Plugin(
        "cmsaas_internal_routes",
        "plugins.internal_routes.internal_routes",
        "InternalRoutes",
    ),
]

plugin_dist = Distribution("plugins")
entrypoints = dict()
logger.info("Adding plugins to entrypoint")
for plugin in cloudumi_plugins:
    logger.debug(f"Lazy loading {plugin.Name} as entrypoint")
    entrypoint = EntryPoint(
        plugin.Name, plugin.ModulePath, tuple([plugin.Attr]), dist=plugin_dist
    )
    entrypoints[plugin.Name] = entrypoint
