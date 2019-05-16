import sys
import os
import json
import logging
from notest.lib.utils import read_test_file

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
from notest.lib.parsing import safe_to_bool
from notest.master import run_testsets, parse_testsets
from notest.plugin_registery import auto_load_ext

"""
Executable class, ties everything together into the framework.
Module responsibilities:
- Read & import test test_files
- Parse test configs
- Provide executor methods for sets of tests and benchmarks
- Collect and report on test/benchmark results
- Perform analysis on benchmark results
"""
HEADER_ENCODING = 'ISO-8859-1'  # Per RFC 2616
LOGGING_LEVELS = {'debug': logging.DEBUG,
                  'info': logging.INFO,
                  'warning': logging.WARNING,
                  'error': logging.ERROR,
                  'critical': logging.CRITICAL}

DEFAULT_LOGGING_LEVEL = logging.INFO

logger = logging.getLogger('notest.main')
logging_config = {
    'level': DEFAULT_LOGGING_LEVEL,
    'format': "%(asctime)s - %(message)s"
}

CONFIG = None


def load_config(config_file):
    global CONFIG
    if not CONFIG:
        if os.path.isfile(config_file):
            with open(config_file, "r") as fd:
                data = fd.read()
                if isinstance(data, bytes):
                    data = data.decode()
                data = json.loads(data)
                CONFIG = data
    return CONFIG


def notest_run(args):
    """
        Execute a test against the given base url.

        Keys allowed for args:
            test_structure          - REQUIRED - Test file (yaml/json)
            working_directory      - OPTIONAL
            interactive   - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
            skip_term_colors - OPTIONAL - mode that turn off the output term colors
            config_file   - OPTIONAL
            ssl_insecure   - OPTIONAL
            ext_dir   - OPTIONAL
            default_base_url   - OPTIONAL
            request_client   - OPTIONAL  default requests
            loop_interval   - OPTIONAL   default 2s
        """

    test_structure = args.get("test_structure")
    assert test_structure

    config_file = None
    if 'config_file' in args and args['config_file'] is not None:
        config_file = args['config_file']
    else:
        config_file = "config.json"
    config_from_file = load_config(config_file)
    if config_from_file:
        for k, v in args.items():
            if v:
                config_from_file[k] = v
        args = config_from_file

    working_directory = None
    if 'working_directory' in args and args['working_directory']:
        working_directory = args['working_directory']

    testsets = parse_testsets(test_structure,
                              working_directory=working_directory)

    # Override configs from command line if config set
    for t in testsets:
        if 'interactive' in args and args['interactive'] is not None:
            t.config.interactive = safe_to_bool(args['interactive'])

        if 'verbose' in args and args['verbose'] is not None:
            t.config.verbose = safe_to_bool(args['verbose'])

        if 'ssl_insecure' in args and args['ssl_insecure'] is not None:
            t.config.ssl_insecure = safe_to_bool(args['ssl_insecure'])

        if 'ext_dir' in args and args['ext_dir'] is not None:
            auto_load_ext(args['ext_dir'])

        if 'default_base_url' in args and args['default_base_url'] is not None:
            t.config.set_default_base_url(args['default_base_url'])

        if 'request_client' in args and args['request_client'] is not None and not t.config.request_client:
            t.config.request_client = args['request_client']

        if 'loop_interval' in args and args['loop_interval']:
            t.config.loop_interval = int(args['loop_interval'])

        if 'skip_term_colors' in args and args[
            'skip_term_colors'] is not None:
            t.config.skip_term_colors = safe_to_bool(
                args['skip_term_colors'])

    # Execute all testsets
    failures_count = run_testsets(testsets)

    return failures_count