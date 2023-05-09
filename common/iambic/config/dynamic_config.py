from iambic.config.dynamic_config import load_config as load_config_template
from iambic.config.utils import resolve_config_template_path


async def load_iambic_config(repo_path: str):
    config_template_path = await resolve_config_template_path(str(repo_path))
    return await load_config_template(
        config_template_path,
        configure_plugins=False,
        approved_plugins_only=True,
    )
