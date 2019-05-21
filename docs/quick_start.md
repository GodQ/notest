
# NoTest Install
notest是以pip包的形式来发布。

* pip install -U notest

# Usage

## Command Mode

```bash
(notest) λ python notest\main.py examples\use_include.yaml -h

Usage: notest test_filen.yaml [options]

Options:
  -h, --help            show this help message and exit
  --log=LOG             Logging level
  -i, --interactive     Interactive mode
  -t TEST_FILE, --test-file=TEST_FILE
                        Test file to use, yaml or json file
  --ssl-insecure        Disable cURL host and peer cert verification
  --ext-dir=EXT_DIR     local extensions dir, default ./ext
  --env-vars=ENV_VARS   environment variables, format: json, will be injected
                        to config-variable-binds of testset
  --env-file=ENV_FILE   environment variables file, will be injected to
                        config-variable-binds of testset
  -b DEFAULT_BASE_URL, --default-base-url=DEFAULT_BASE_URL
                        default base url, if not specified, use the config in
                        test file
  -c CONFIG_FILE, --config-file=CONFIG_FILE
                        config file
  -l LOOP_INTERVAL, --loop-interval=LOOP_INTERVAL
                        loop_interval, default 2s
  -r REQUEST_CLIENT, --request-client=REQUEST_CLIENT
                        request_client, select one in [requests, pycurl],
                        default requests. If use pycurl, you should install
                        pycurl first by "pip install -U pycurl"
  -v OVERRIDE_CONFIG_VARIABLE_BINDS, --override-config-variable-binds=OVERRIDE_CONFIG_VARIABLE_BINDS
                        override_config_variable_binds, format -o key1=value1
                        -o key2=value2
```

## Python Lib Mode

```python
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
```


# Quick Start

## The First Testcase
编写第一个testcase:  
测试调用搜索网页搜索关键字功能

* 创建yaml文件github_search.yaml
```yaml
- config:
     testset: "Quickstart github search test"
     default_base_url: 'https://github.com'

- test:
     group: "Quickstart"
     name: "Basic get"
     headers: {'Content-Type': 'text/html; charset=utf-8'}
     url: "/search?q=notest&type=Topics"
     method: "GET"
     expected_status: [200]

```
	
	
## Run
* 运行：
```bash
notest github_search.yaml 
```
默认输出为：

```log
2019-05-10 09:14:02,234 -
Test Name: Basic get
  Request= GET https://github.com/search?q=notest&type=Topics
  Group=Quickstart
  HTTP Status Code: 200
  passed

Test Group Quickstart SUCCEEDED: : 1/1 Tests Passed!
```










