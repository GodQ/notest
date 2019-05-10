
# NoTest Install
notest是以pip包的形式来发布。

* pip install notest


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










