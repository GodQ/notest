import mysql.connector
from mysql.connector import errorcode
import logging

logger = logging.Logger("mysql_lib")


class MysqlClient:
    def __init__(self, config):
        self.connection = None
        self.cursor = None
        if not config:
            raise Exception("No MySQL config")
        self.config = config

    def __enter__(self):
        self.connect(self.config)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self, config=None):
        if not config:
            config = self.config
        try:
            connection = mysql.connector.connect(**config)
            self.connection = connection
            self.cursor = self.get_cursor()
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error(
                    "Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error("Database does not exist")
            elif err.errno == errorcode.CR_CONN_HOST_ERROR:
                logger.error("Host Connection Error")
            else:
                logger.error(err.errno)
            raise err
        return self.connection

    def close(self):
        try:
            self.connection.close()
            logger.debug("Connection Closed")
        except Exception as e:
            logger.error(str(e))

    def get_cursor(self):
        if not self.cursor:
            if not self.connection:
                self.connection = self.connect(None)
            self.cursor = self.connection.cursor()
        return self.cursor

    def execute(self, sql):
        try:
            cursor = self.get_cursor()
            cursor.execute(sql)
            self.connection.commit()
        except Exception as e:
            logger.error(str(e))
            raise e

    def query(self, sql, return_dict_list=False):
        cursor = self.get_cursor()
        cursor.execute(sql)
        ret = cursor.fetchall()
        if return_dict_list is True:
            r = list()
            col_names = cursor.column_names
            for line in ret:
                t = dict(zip(col_names, line))
                r.append(t)
            ret = r
        return ret


if __name__ == '__main__':
    # docker run -it --name mysql -p 3306:3306 -p 33060:33060 -e MYSQL_ROOT_PASSWORD=password -e MYSQLOST=0.0.0.0 mysql:5.7
    config = {
        'user': 'root',
        'password': 'password',
        'host': '192.168.99.101',
        'database': 'test',
        'use_pure': False
    }

    with MysqlClient(config) as cli:
        # cli.execute(
        #     "insert into sites(name, url) values('baidu', 'www.baidu.com')")
        # cli.execute(
        #     "insert into sites(name, url) values('google', 'www.google.com')")
        ret = cli.query("select * from sites where name='baidu'")
        print(type(ret))
        for i in ret:
            print(i)

        ret = cli.query("select * from sites where name='baidu'", return_dict_list=True)
        print(type(ret))
        for i in ret:
            print(i)
