import traceback
import json
import sys

PYTHON_MAJOR_VERSION = sys.version_info[0]

import yaml
import ast
import jmespath
from pyresttest.lib.mysql_lib import MysqlClient

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
                return res
        except Exception as e:
            raise ValueError("Invalid query: " + query + " : " + str(e))

    @classmethod
    def parse(cls, config):
        if not isinstance(config, dict):
            raise Exception("MySQL Extractor must be a dict, not {} {}".
                            format(type(config), config))
        if "sql" not in config or "config" not in config:
            raise Exception("MySQL Extractor must have sql and config")

        entity = MySQLQueryExtractor()
        entity.mysql_config = config["config"]
        entity.sql = config["sql"]
        # configure_base will solve template
        return cls.configure_base(entity.sql, entity)


EXTRACTORS = {'mysql': MySQLQueryExtractor.parse}
