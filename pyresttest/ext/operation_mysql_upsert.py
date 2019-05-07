import json

from pyresttest.lib.utils import templated_var
from pyresttest.lib.mysql_lib import MysqlClient

'''
- operation:
    - type: "mysql_upsert"
    - config: '{"user": "root", "password": "password", "host": "192.168.99.101", "database": "test"}'
    - sql: 'insert into sites(name, url) values("a", "a.com")'
'''


def mysql_upsert(config, context=None):
    print("Run mysql_upsert")
    assert isinstance(config, dict)
    assert "config" in config
    assert "sql" in config
    sql = templated_var(config['sql'], context)
    mysql_config = templated_var(config['config'], context)
    mysql_config = json.loads(mysql_config)
    with MysqlClient(mysql_config) as cli:
        cli.execute(sql)


OPERATIONS = {'mysql_upsert': mysql_upsert}
