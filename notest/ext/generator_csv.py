
import os
import logging
import json
import csv

logger = logging.Logger("csv_generator")

from notest.lib.mysql_lib import MysqlClient
from notest.lib.utils import templated_var
from notest import generators


'''
 - generators:
        - task_id: {type: 'number_sequence', start: 10}
        - task_name:
            type: 'csv'
            file: 'test.csv'
            return_dict: false
'''


def factory_csv_generator(csv_path):
    def csv_generator():
        with open(csv_path, "r") as fd:
            reader = csv.DictReader(fd)
            for line in reader:
                yield line
    return csv_generator


def parse_csv_generator(config, variable_binds):
    """ Parses configuration options for a mysql_query generator """
    csv_file = config.get('file')
    working_directory = variable_binds.get('working_directory', '.')
    csv_path = os.path.join(working_directory, csv_file)
    return factory_csv_generator(csv_path)()


GENERATORS = {'csv': parse_csv_generator}
