import os

from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import ImmutableSandboxedEnvironment

TEMPLATE_DIR = os.path.dirname(__file__)

env = ImmutableSandboxedEnvironment(
    loader=FileSystemLoader("common/templates"),
    extensions=["jinja2.ext.loopcontrols"],
    autoescape=select_autoescape(),
)

new_user_with_password_email_template = env.get_template(
    "new_user_with_password_email_template.html.j2"
)

generic_email_template = env.get_template("generic_email_template.html.j2")
