import sys
import os
import logging

logger = logging.Logger("plugin_registry")

ESCAPE_DECODING = 'unicode_escape'

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from notest import generators
from notest import validators
from notest import operations


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def register_extensions(modules):
    """ Import the modules and register their respective extensions """
    if isinstance(modules, str):  # Catch supplying just a string arg
        modules = [modules]
    for ext in modules:
        # Get the package prefix and final module name
        segments = ext.split('.')
        module = segments.pop()
        package = '.'.join(segments)
        # Necessary to get the root module back
        module = __import__(ext, globals(), locals(), package)

        # Extensions are registered by applying a register function to sets of
        # registry name/function pairs inside an object
        extension_applies = {
            'VALIDATORS': validators.register_validator,
            'COMPARATORS': validators.register_comparator,
            'VALIDATOR_TESTS': validators.register_test,
            'EXTRACTORS': validators.register_extractor,
            'GENERATORS': generators.register_generator,
            'OPERATIONS': operations.register_operations
        }

        has_registry = False
        for registry_name, register_function in extension_applies.items():
            if hasattr(module, registry_name):
                registry = getattr(module, registry_name)
                for key, val in registry.items():
                    register_function(key, val)
                    logger.warning("Register {} {} to module {}".format(
                        registry_name.lower(), key, ext
                    ))
                if registry:
                    has_registry = True

        if not has_registry:
            raise ImportError(
                "Extension to register did not contain any registries: {0}".format(
                    ext))


def auto_load_ext(ext_dir=os.path.join(BASE_DIR, "ext")):
    sys.path.append(ext_dir)
    for fname in os.listdir(ext_dir):
        path = os.path.join(ext_dir, fname)
        if os.path.isfile(path) and fname.endswith(".py") and \
                fname != "__init__.py":
            module_name = [fname.strip(".py")]
            try:
                register_extensions(".".join(module_name))
            except ImportError as e:
                logger.error(str(e))
    print()


auto_load_ext(ext_dir=os.path.join(BASE_DIR, "ext"))
