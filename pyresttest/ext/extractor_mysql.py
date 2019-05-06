import traceback
import json
import sys

PYTHON_MAJOR_VERSION = sys.version_info[0]

import yaml
import ast
import jmespath
from pyresttest.lib.mysql_lib import MysqlClient
from pyresttest.lib.utils import templated_var

try:  # First try to load pyresttest from global namespace
    from pyresttest import validators
    from pyresttest import binding
    from pyresttest import parsing
    from pyresttest import contenthandling
except ImportError:  # Then try a relative import if possible
    from .. import validators
    from .. import binding
    from .. import parsing
    from .. import contenthandling


class MySQLQueryExtractor(validators.AbstractExtractor):
    """
    Extractor that uses MySQL SQL query syntax
    """
    extractor_type = 'mysql'

    def __init__(self):
        self.sql = None
        self.mysql_config = None

    def extract_internal(self, query=None, args=None, body=None,
                         headers=None):
        if PYTHON_MAJOR_VERSION > 2:
            if isinstance(query, bytes):
                query = str(query, 'utf-8')

        try:
            with MysqlClient(self.mysql_config) as cli:
                res = cli.query(query)
                if len(res) == 0:
                    raise Exception(
                        "No data queried in MySQL by '{}'!".format(query))
                res = res[0]
                if isinstance(res, tuple):
                    res = res[0]
                return res
        except Exception as e:
            raise ValueError("Invalid query: " + query + " : " + str(e))

    @classmethod
    def parse(cls, config):
        mysql_config = config.get(u'config')
        mysql_config = templated_var(mysql_config)
        if isinstance(mysql_config, str):
            mysql_config = json.loads(mysql_config)
        sql = config.get(u'sql')
        sql = templated_var(sql)

        entity = MySQLQueryExtractor()
        entity.mysql_config = mysql_config
        entity.sql = sql
        # configure_base will solve template
        return cls.configure_base(entity.sql, entity)


EXTRACTORS = {'mysql': MySQLQueryExtractor.parse}
