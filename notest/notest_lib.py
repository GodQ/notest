import sys
import os
import json
import logging

from notest.master import run_testsets, parse_testsets
from notest.config_loader import load_args, load_config_file

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))

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


def notest_run(args):
    """
        Execute a test against the given base url.

        Keys allowed for args:
            test_structure          - REQUIRED - Test file (yaml/json)
            working_directory      - OPTIONAL
            override_config_variable_binds  - OPTIONAL - override variable_binds of config in test file
            interactive   - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
                                     please set False when not used by command
            config_file   - OPTIONAL
            env_vars     -  OPTIONAL  format: json
            env_file     -  OPTIONAL   format: json str or dict
            ssl_insecure   - OPTIONAL  default True
            ext_dir   - OPTIONAL
            default_base_url   - OPTIONAL
            request_client   - OPTIONAL  default requests
            loop_interval   - OPTIONAL   default 2s
        """
    # import pprint
    # pprint.pprint(args)

    test_structure = args.get("test_structure")
    assert test_structure

    config_file = None
    if 'config_file' in args and args['config_file'] is not None:
        config_file = args['config_file']
    else:
        config_file = "config.json"
    config_from_file = load_config_file(config_file)
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
    for testset in testsets:
        load_args(testset, args)

    # Execute all testsets
    total_results = run_testsets(testsets)

    return total_results