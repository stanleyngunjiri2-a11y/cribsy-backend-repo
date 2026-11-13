"""Every file in this folder that defines `bp` and `URL_PREFIX` is registered automatically,
so team members never edit this file."""
import importlib
import pkgutil


def register_blueprints(app):
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        if hasattr(module, "bp"):
            app.register_blueprint(module.bp, url_prefix=module.URL_PREFIX)
