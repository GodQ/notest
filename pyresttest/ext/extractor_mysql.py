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
    from pyresttest import context
    from pyresttest import parsing
    from pyresttest import contenthandling
except ImportError:  # Then try a relative import if possible
    from .. import validators
    from .. import context
    from .. import parsing
    from .. import contenthandling


class MySQLQueryExtractor(validators.AbstractExtractor):
    """
    Extractor that uses MySQL SQL query syntax
    """
    extractor_type = 'mysql'

    def __init__(self):
        self.query = None
        self.mysql_config = None

    def extract_internal(self, body=None, headers=None, context=None):
        self.query = templated_var(self.query, context)
        self.mysql_config = templated_var(self.mysql_config, context)
        self.mysql_config = json.loads(self.mysql_config)
        try:
            with MysqlClient(self.mysql_config) as cli:
                res = cli.query(self.query)
                if len(res) == 0:
                    raise Exception(
                        "No data queried in MySQL by '{}'!".format(self.query))
                res = res[0]
                if isinstance(res, tuple):
                    res = res[0]
                return res
        except Exception as e:
            raise ValueError("Invalid query: '" + self.query + "' : " + str(e))

    @classmethod
    def parse(cls, config):
        mysql_config = config.get('config')
        sql = config.get('query')
        entity = MySQLQueryExtractor()
        entity.mysql_config = mysql_config
        entity.query = sql
        return entity


EXTRACTORS = {'mysql': MySQLQueryExtractor.parse}
