import json
from notest.lib.mysql_lib import MysqlClient
from notest.lib.utils import templated_var
from notest import validators


'''
- extract_binds:
        - post_task_title:
            test:
              query: 'test-aaa'
'''


class TestExtractor(validators.AbstractExtractor):
    """
    Extractor that return self.query
    """
    extractor_type = 'test-godq'

    def __init__(self):
        self.query = None
        self.mysql_config = None

    def extract_internal(self, body=None, headers=None, context=None):
        self.query = templated_var(self.query, context)
        return self.query

    @classmethod
    def parse(cls, config):
        entity = TestExtractor()
        entity.query = config.get('query', 'test-godq')
        return entity


EXTRACTORS = {'test-godq': TestExtractor.parse}
