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


def load_env_vars(testset_config, env_vars):
    print("Loading env vars: {}".format(env_vars))
    if isinstance(env_vars, str):
        env_vars = json.loads(env_vars)
    assert isinstance(env_vars, dict)
    for k, v in env_vars.items():
        testset_config.set_variable_binds(k, v)


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

    env_vars = None

    # Override configs from command line if config set
    for testset in testsets:
        if 'interactive' in args and args['interactive'] is not None:
            ia = args['interactive']
            if isinstance(ia, str):
                ia = safe_to_bool(args['interactive'])
            assert isinstance(ia, bool)
            testset.config.interactive = ia

        if 'verbose' in args and args['verbose'] is not None:
            testset.config.verbose = safe_to_bool(args['verbose'])

        if 'ssl_insecure' in args and args['ssl_insecure'] is not None:
            testset.config.ssl_insecure = safe_to_bool(args['ssl_insecure'])

        if 'ext_dir' in args and args['ext_dir'] is not None:
            if not os.path.exists(args['ext_dir']):
                msg = "Plugin Folder ext_dir can not found, path:'{}'  ...... Skipped\n".format(args['ext_dir'])
                logger.error(msg)
            elif os.path.isdir(args['ext_dir']):
                auto_load_ext(args['ext_dir'])
            else:
                msg = "Option ext_dir must be folder, path:'{}'".format(args['ext_dir'])
                logger.error(msg)
                raise Exception(msg)

        if 'default_base_url' in args and args['default_base_url'] is not None:
            testset.config.set_default_base_url(args['default_base_url'])

        if 'env_file' in args and args['env_file'] is not None:
            load_env_vars(testset.config, read_test_file(args['env_file']))

        if 'env_vars' in args and args['env_vars'] is not None:
            load_env_vars(testset.config, args['env_vars'])

        if 'override_config_variable_binds' in args and args['override_config_variable_binds'] is not None:
            override_vars = args['override_config_variable_binds']
            if isinstance(override_vars, bytes):
                override_vars = override_vars.decode()
            if isinstance(override_vars, str):
                try:
                    override_vars = json.loads(override_vars)
                except Exception as e:
                    logger.error("Load json error, {} {} ".format(str(e), override_vars))
                    raise e
            elif isinstance(override_vars, list):
                vd = dict()
                for v in override_vars:
                    t = v.split("=")
                    if len(t) != 2:
                        raise Exception("Option override_config_variable_binds can not be parsed! {}".format(override_vars))
                    vd[t[0]] = t[1]
                override_vars = vd
            assert isinstance(override_vars, dict)
            for k, v in override_vars.items():
                testset.config.set_variable_binds(k, v)

        if 'request_client' in args and args['request_client'] is not None and not testset.config.request_client:
            testset.config.request_client = args['request_client']

        if 'loop_interval' in args and args['loop_interval']:
            testset.config.loop_interval = int(args['loop_interval'])

    # Execute all testsets
    total_results = run_testsets(testsets)

    return total_results