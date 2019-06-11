
import sys
import logging
import json

logger = logging.Logger("mysql_generator")

from notest.lib.mysql_lib import MysqlClient
from notest.lib.utils import templated_var
from notest import generators


'''
 - generators:
        - task_id: {type: 'number_sequence', start: 10}
        - task_name:
            type: 'mysql'
            query: 'select name from sites'
            config: '$mysql_config'
'''


def parse_mysql_query_generator(config, variable_binds):
    """ Parses configuration options for a mysql_query generator """
    mysql_config = config.get('config')
    sql = config.get('query')
    return_dict_list = config.get('return_dict_list', False)
    mysql_config = templated_var(mysql_config, variable_binds)
    if isinstance(mysql_config, str):
        mysql_config = json.loads(mysql_config)
    sql = templated_var(sql)
    if isinstance(return_dict_list, str):
        return_dict_list = True if return_dict_list.lower() == 'true' else False
    try:
        with MysqlClient(mysql_config) as cli:
            r = None
            if return_dict_list is False:
                res = cli.query(sql)
                r = list()
                for i in res:
                    if isinstance(i, tuple):
                        i = i[0]
                    r.append(i)
            else:
                r = cli.query(sql, return_dict_list=return_dict_list)
            if len(r) == 0:
                raise Exception("No data queried in MySQL by '{}'!".format(sql))
            return generators.factory_fixed_sequence(r)()
    except Exception as e:
        logger.error(str(e))
        raise ValueError("Invalid query: " + sql + " : " + str(e))


GENERATORS = {'mysql': parse_mysql_query_generator}
