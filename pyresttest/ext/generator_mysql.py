
import sys
import logging
import json

logger = logging.Logger("mysql_generator")

PYTHON_MAJOR_VERSION = sys.version_info[0]

from pyresttest.lib.mysql_lib import MysqlClient
from pyresttest.lib.utils import templated_var

try:  # First try to load pyresttest from global namespace
    from pyresttest import generators
except ImportError:  # Then try a relative import if possible
    from .. import generators


def parse_mysql_query_generator(config, variable_binds):
    """ Parses configuration options for a mysql_query generator """
    mysql_config = config.get('config')
    mysql_config = templated_var(mysql_config, variable_binds)
    if isinstance(mysql_config, str):
        mysql_config = json.loads(mysql_config)
    sql = config.get('query')
    sql = templated_var(sql)
    try:
        with MysqlClient(mysql_config) as cli:
            res = cli.query(sql)
            r = list()
            for i in res:
                if isinstance(i, tuple):
                    i = i[0]
                r.append(i)
            if len(r) == 0:
                raise Exception("No data queried in MySQL by '{}'!".format(sql))
            return generators.factory_fixed_sequence(r)()
    except Exception as e:
        logger.error(str(e))
        raise ValueError("Invalid query: " + sql + " : " + str(e))


def parse_mysql_upsert_generator(config, variable_binds):
    """ Parses configuration options for a mysql_query generator """
    mysql_config = config.get('config')
    mysql_config = templated_var(mysql_config, variable_binds)
    if isinstance(mysql_config, str):
        mysql_config = json.loads(mysql_config)
    sql = config.get('upsert')
    sql = templated_var(sql)
    try:
        with MysqlClient(mysql_config) as cli:
            cli.execute(sql)
        return generators.factory_fixed_sequence([1])()
    except Exception as e:
        logger.error(str(e))
        raise ValueError("Invalid query: " + sql + " : " + str(e))


GENERATORS = {'mysql': parse_mysql_query_generator,
              'mysql_upsert': parse_mysql_upsert_generator}
