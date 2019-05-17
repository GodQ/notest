from notest.notest_lib import notest_run
import logging

logging.basicConfig(level=logging.INFO)

args = {
    # 'config_file': '../examples/config.json',
    # 'default_base_url': None,
    'override_config_variable_binds': {
        'title': 'GodQ-override'
    },
    # 'ext_dir': None,
    'loop_interval': 1,
    # 'request_client': None,
    # 'working_directory': '../examples',
    'test_structure': [{'config': {'default_base_url': 'http://localhost:5000',
                                   'generators': [{'id': {'start': 10,
                                                          'type': 'number_sequence'}}],
                                   'testset': 'Quickstart app tests',
                                   'variable_binds': {'done': 'true',
                                                      'title': 'GodQ'}}},
                       {'test': {'expected_status': [201],
                                 'method': 'POST',
                                 'name': 'post ready task',
                                 'url': '/delay_task',
                                 'body': '$title'}},
                       {'test': {'expected_status': 200,
                                 'headers': {'Content-Type': 'application/json',
                                             'Token': 123},
                                 'loop_until': [{'extract_test': {'jsonpath_mini': 'state',
                                                                  'test': 'exists'}},
                                                {'compare': {'comparator': 'str_eq',
                                                             'expected': 'ready',
                                                             'jsonpath_mini': 'state'}}],
                                 'method': 'GET',
                                 'name': 'get ready task',
                                 'url': '/delay_task',
                                 'body': '{"title": "$title"}'}}]

}

total_results = notest_run(args)
print("TestCase Count: {}".format(total_results.test_count))
print("Failure Count: {}".format(total_results.failure_count))
print("Failure List: {}".format(total_results.get_failures()))