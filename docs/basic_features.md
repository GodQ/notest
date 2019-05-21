# Basic Features

## 用例结构介绍
```yaml
- config:
     testset: ...
     variable_binds: ...
     default_base_url: ...
     generators: ...
- operation:
     ...
- test:
     generator_binds: ...
     group: ...
     name: ...
     url: ...
     method: ...
     headers: ...
     body: ...
     expected_status: ...
     validators: ...
     extract_binds: ...
- test:
     ...
- test:
     ...
```
其中，
- config为对testset的定义，
包括名称、全局变量、默认domain name，数据驱动生成器generators等

- test为一个请求的定义，
包括http请求中的url、method、headers、body，引用生成器的generator_binds，返回码验证expected_status，各种验证器validators，以及导出内容到变量的extract_binds等

- operation
该项目为一系列的工具类操作，比如数据库插入修改等可以使用type为mysql_upsert的operation

- import
允许用户import其他的用例文件，import的文件会生成一个新的testset，类似于子进程，上下文独立，执行的result会汇总

- include
功能类似import，允许用户include其他的用例文件，区别是不会生成一个新的testset，会共享同一份上下文

## 概念介绍
- testset
一个testset相当于一个测试场景，在config中的testset用于定义它的名称

- variable_binds
在config中定义全局变量，使用一个dict方式定义，有个限制就是不能相互引用，需要是静态的

- generators
在config模块中数据生成器定义，每个生成器相当于定义了一个python的迭代器generator，此时并不会调用next来获取具体数据，仅仅是定义。比如定义如下生成器：
```yaml
generators:
   - 'task_id_generator': {type: 'number_sequence', start: 10}
```
意思就是定义一个生成器名叫task_id_generator，类型为number_sequence，作用是从10每次使用的时候返回一个整数，一次增大，10、11、12......

- generator_binds
字段generator_binds存在于test模块中，用于调用config中定义的generator的next生成具体数据。该方法一直到运行时才会调用。生成的数据会放在一个全局变量中。比如
```yaml
generator_binds:
	- task_id: task_id_generator
```
为调用上面定义的task_id_generator生成器，将获取的数据放在全局变量task_id中，task_id可以在下文引用

- expected_status
test中定义的期望的返回码，用于校验http status code

- validators
test中定义的验证器，可以有多个，运行时会依次进行校验。比如：
```yaml
     validators:
        - extract_test: {jsonpath_mini: "info.0.title", test: "exists"}
        - compare:
             jsonpath_mini: "info.0.id"
             comparator: "str_eq"
             expected: '$task_id'
```
定义了两个验证器，第一个类型为extract_test，即验证jsonpath字段info.0.title是否可以导出， 第二个验证器类型为compare，比较两个字段，其中jsonpath_mini: "info.0.id"为从http response body中拿出的数据，comparator: "str_eq"为判断的方法，expected: '$task_id'为期望值

- extract_binds
test中定义的导出数据到全局变量的导出器，可以有多个。比如：
```yaml
extract_binds:
   - post_task_id: {jsonpath_mini: 'info.0.id'}
```
为请求执行完成后将jsonpath字段info.0.id对应的内容保存到全局变量post_task_id中，以供下文使用。

各项特性使用说明请参照[NoTest高级特性](advanced_features.md#advanced-features)

## Step by Step 写测试
### Hello NoTest
最简单的请求可以参照[first.yaml](../examples/first.yaml)，只包含一个http请求，如下：
```yaml
- config:
     testset: "Quickstart app tests"
     default_base_url: 'http://localhost:5000'

- test:
     group: "Quickstart"
     name: "Basic get"
     headers: {'Content-Type': 'application/json', "Token": 123}
     url: "/tasks"
	 expected_status: [200]

```
group字段用于对请求进行分类，比如一个测试场景若需要对多个host发送请求，可以设置成不同的group，从而得到的执行结果会按照group进行分类统计，从而得到更精确的测试统计。

运行notest examples/first.yaml得到结果：
```bash
 λ notest examples/first.yaml
Register extractors jmespath to module extractor_jmespath
Register extractors mysql to module extractor_mysql
Register generators mysql to module generator_mysql
Register operations mysql_upsert to module operation_mysql_upsert
Register operations print_operation to module operation_print
Register validators json_schema to module validator_jsonschema

2019-05-10 14:57:03,126 -
Test Name: Basic get
  Request= GET http://localhost:5000/tasks
  Group=Quickstart
  HTTP Status Code: 200
  passed

Test Group Quickstart SUCCEEDED: : 1/1 Tests Passed!
```

###多请求测试
一般测试场景都会是多个请求组合而来，[多测试请求案例](../examples/multi-test.yaml)展示了一个创建任务、查询任务、删除任务、清理测试环境的流程测试。这里就不再粘贴测试执行了。

### 测试场景中使用全局变量
上面的测试都是hard code将测试数据写死在用例中了，而若需要修改测试数据则需要改很多地方，为了应对这种需求，我们可以使用全局变量来解决。参见[全局变量案例](../examples/use_variable.yaml)
在config中定义如下配置：
```yaml
variable_binds:
        title: 'Gaius-Test'
        done: 'true'
        task_id: 9999
```
在test定义中使用如下格式：
```yaml
- test:
     group: "Quickstart"
     name: "post"
     url: "/tasks"
     method: "POST"
     headers: {'Content-Type': 'application/json', "Token": 123}
     body: '{"title": "$title", "id": "$task_id", "done": "$done"}'
     expected_status: [201]
- test:
     group: "Quickstart"
     name: "get"
     headers: {'Content-Type': 'application/json', "Token": 123}
     url: "/task/$task_id"
     method: "GET"
     expected_status: [200]
```
从而实现数据只定义一次的目标

### 使用多种验证器
上文中我们仅仅验证了http请求的响应码，而很多场景下我们需要对body和header做验证，我们可以使用validator来多维度验证结果，参考[使用验证器案例](../examples\use_validator.yaml)。需要在test中如下定义：
```yaml
validators:
        # Test key does not exist
        - extract_test: {jsonpath_mini: "info.0.title", test: "exists"}
        - compare:
             jsonpath_mini: "info.0.id"
             comparator: "str_eq"
             expected: '$task_id'
```
这个案例中添加了两个验证器，extract_test为验证字段是否可存在，compare为比较jsonpath搜索"info.0.id"的内容与$task_id是否相等

### 使用数据导出到变量功能
大部分场景中测试请求需要使用上一个或者多个请求的结果来串联上下文，参考[使用extractor案例](../examples/use_extractor.yaml)。在test最后加上
```yaml
extract_binds:
        - post_task_id: {jsonpath_mini: 'info.0.id'}
```
即可将response body中按照jsonpath方式获取字段，并放到全局变量post_task_id中，下文可以直接用$post_task_id来访问。

### 导出mysql数据库中数据
mysql导出操作已经在notest中原生支持，参考[MySQL导出案例](../examples/mysql_extractor.yaml)。具体定义如下：
在config中定义全局变量mysql_config
```yaml
variable_binds:
        .....
        mysql_config: '{"user": "root", "password": "password", "host": "192.168.99.101", "database": "test"}'
```
在test中定义extract_binds
```yaml
extract_binds:
        - post_task_title:
            mysql:
              query: 'select name from sites limit 1'
              config: '$mysql_config'
```
将mysql中查出的数据存到变量post_task_title中。需要自己设置好sql。该功能有个限制，sql查询结果需要只有一个数据，否则无法进行比较。

### 验证mysql数据库中数据
验证功能都可以使用validator，mysql操作已经在notest中原生支持，参考[MySQL验证案例](../examples/mysql_validator.yaml)。具体定义如下：
在config中定义全局变量mysql_config
```yaml
variable_binds:
        .....
        mysql_config: '{"user": "root", "password": "password", "host": "192.168.99.101", "database": "test"}'
```
在test中定义validator
```yaml
validators:
        - compare:
             jsonpath_mini: "info.0.id"
             comparator: "str_eq"
             expected:
                mysql:
                  query: 'select name from sites limit 1'
                  config: '$mysql_config'
```
在该例子中在expected中使用了mysql做验证，需要自己设置好sql。该功能有个限制，sql查询结果需要只有一个数据，否则无法进行比较。
validator中使用的都是extractor，所以所有extract_binds支持的操作都可以直接在validator中引用。

### 使用生成器generator产生数据
很多时候需要使用随机数据来进行测试，这种情况就需要使用生成器generator了。参考[使用生成器generator](../examples/use_generator.yaml)。在config中定义生成器
```yaml
generators:
        - task_id_generator: {type: 'random_int'}
        - title_generator: {type: 'random_text', length: 6, character_set: 'ascii_uppercase'}
```
在test中使用生成器
```yaml
- test:
     generator_binds:
        - task_id: task_id_generator
        - title: title_generator
     group: "Quickstart"
     name: "post"
     url: "/tasks"
     method: "POST"
     headers: {'Content-Type': 'application/json', "Token": 123}
     body: '{"title": "$title", "id": "$task_id", "done": "$done"}'
```
从而task id每次都是随机int，而title每次都是随机大写字母字符串

### 使用loop until循环执行功能
很多任务处理时间较长的情况下，api会设计为post+get的异步方式。post一个任务，get用来查询任务状态。此时，测试用例会设计成一个post+若干个get的形式，每次get后判断返回值是否满足某些添加而确定是否继续执行。
针对这种情况，notest提供了test中的loop_until关键字来实现。参考[使用loop until循环执行功能](../examples/use_test_loop_until.yaml)在test中定义loop_until条件：
```yaml
- test:
    name: "post ready task"
    url: "/delay_task"
    method: "POST"
    expected_status: [201]

- test:
     name: "get ready task"
     url: "/delay_task"
     method: "GET"
     headers: {'Content-Type': 'application/json', "Token": 123}
     expected_status: [200]
     loop_until:
        - compare:
             jsonpath_mini: "state"
             comparator: "str_eq"
             expected: 'ready'
```
loop_until调用validators实现条件判断，所以格式与validators完全一致。允许多个条件，只有所有条件都满足才会跳出循环继续下一个test。

### 按需sleep
针对上面的post+get类型的case，如果可以确定在某个时间内会处理完成，那可以使用sleep_operation来实现。使用方式如下：
```yaml
- operation:
     type: "sleep_operation"
     seconds: 5
```
将该operation放在post和get两个test中间即可。



## 来一个综合测试用例
```yaml
- config:
     testset: "Quickstart app tests"
     variable_binds:
        title: 'Gaius-Test'
        done: 'true'
     default_base_url: 'http://localhost:5000'
     generators:
        # Generator named 'id' that counts up from 10
        - 'task_id_generator': {type: 'random_int'}

- operation:
     type: "print_operation"
     print: '$title'

- test:
     generator_binds:
        - task_id: task_id_generator
     group: "Quickstart"
     name: "post"
     url: "/tasks"
     method: "POST"
     headers: {'Content-Type': 'application/json', "Token": 123}
     body: '{"title": "$title", "id": "$task_id", "done": "$done"}'
     expected_status: [201]
     validators:
        - extract_test: {jsonpath_mini: "info.0.title", test: "exists"}
        - compare:
            - jsonpath_mini: "info.0.id"
            - comparator: "str_eq"
            - expected: '$task_id'
     extract_binds:
        - post_task_id: {jsonpath_mini: 'info.0.id'}

- test:
     group: "Quickstart"
     name: "get"
     headers: {'Content-Type': 'application/json', "Token": 123}
     url: "/task/$post_task_id"
     method: "GET"
     expected_status: [200]

- test:
     group: "Quickstart"
     name: "clear all"
     headers: {'Content-Type': 'application/json', "Token": 123}
     url: "/clear_all"
     method: "POST"
     expected_status: [204]
```
