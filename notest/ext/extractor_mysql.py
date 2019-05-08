import json
from notest.lib.mysql_lib import MysqlClient
from notest.lib.utils import templated_var
from notest import validators


'''
- extract_binds:
        - post_task_id: {jsonpath_mini: 'info.0.id'}
        - post_task_title:
            mysql:
              query: 'select name from sites limit 1'
              config: '$mysql_config'
'''


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
