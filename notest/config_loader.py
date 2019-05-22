import sys
import os
import json
import logging
from notest.lib.utils import read_test_file
from notest.lib.parsing import safe_to_bool
from notest.plugin_registery import auto_load_ext

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))

logger = logging.getLogger('notest.config_loader')


CONFIG = None


def load_config_file(config_file):
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


def load_args(testset, args):
    __load_args(testset, args)
    if not testset.subtestsets:
        return
    for name, subset in testset.subtestsets.items():
        load_args(subset, args)


def __load_args(testset, args):
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

    if testset.config.request_client == "pycurl":
        if "libcurl_path" in args and args['libcurl_path'] is not None:
            sys_path = os.environ.get("PATH")
            if not sys_path:
                sys_path = ""
            if sys.platform.find("win"):
                sep = ';'
            else:
                sep = ':'
            libcurl_path = os.path.abspath(args['libcurl_path'].strip())
            new_sys_path = "{}{}{}".format(sys_path, sep, libcurl_path)
            os.environ['PATH'] = new_sys_path

        if "libcurl_ca_file" in args and args['libcurl_ca_file'] is not None:
            import notest.clients.pycurl_client as pycurl_client
            pycurl_client.libcurl_crt_file = os.path.abspath(args['libcurl_ca_file'])

    if 'loop_interval' in args and args['loop_interval']:
        testset.config.loop_interval = int(args['loop_interval'])