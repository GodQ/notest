# TestSet Layered Structure

对于可复用性高的测试来说，需要将很多公共模块进行抽象和包装，从而增加可维护性。
NoTest提供了两种机制来实现。

## module

为了提升可维护性，一般会将逻辑内聚性高的请求组合成一个模块，来被整体调用。
NoTest中一个模块就是一个测试用例，可以单独调试单独运行。
比如[login模块的封装](../examples/login_module.yaml),

```yaml
- config:
     testset: "Quickstart app tests"
     default_base_url: 'http://localhost:5000'
     variable_binds:
        user: 'aaaa'
        password: 'password'

- test:
     group: "Quickstart"
     name: "clear all"
     headers: {'Content-Type': 'application/json', "Token": 123}
     url: "/clear_all"
     method: "POST"
     expected_status: [204]

- test:
     group: "Quickstart"
     name: "get token"
     headers: {'Content-Type': 'application/json'}
     url: "/token"
     method: "POST"
     body:     #'{"user": "$user","password": "$password"}'
        user: '$user'
        password: '$password'
     expected_status: [201]
     extract_binds:
        - token: {jsonpath_mini: 'Token'}
```

## include
类似于C语言中的宏，被include的用例（场景）的非config的step都会被直接添加到所在场景中，从而实现共享同一份上下文的作用，不需要定义传递数据。
不过该模式要求上下文定义的变量需要提供子场景需要的变量，并且子场景可能会改变上下文中的变量值。
需要注意的是被include的场景的config将被弃用，需要确保变量名称正确。
使用方式参考[include示例](../examples/use_include.yaml)
```yaml
- config:
     testset: "Quickstart app tests"
     default_base_url: 'http://localhost:5000'
     variable_binds:
        user: 'u1'
        password: 'p1'

- include: 'login_module.yaml'

- test:
     group: "Quickstart"
     name: "Basic get"
     headers: {'Content-Type': 'application/json', "Token": '$token'}
     url: "/tasks"
```



## import
类似于子进程模式，被import的场景作为一个独立的testset运行，具有隔离的上下文环境，因此若需要传递数据需要指定入参出参。
使用方式参考[import示例](../examples/use_import.yaml)
```yaml
- config:
     testset: "Quickstart app tests"
     default_base_url: 'http://localhost:5000'
     variable_binds:
        user: 'u1'
        password: 'p1'

- import:
    file: login_module.yaml
    input:
        user: 'u1'
        password: 'p1'
    extract: ['token']

- operation:
    type: "print_operation"
    print: '$token'

- test:
     group: "Quickstart"
     name: "post tasks"
     url: "/tasks"
     method: "POST"
     headers: {'Content-Type': 'application/json', "Token": '$token'}
     body: '{"title": "Gaius", "id": 999, "done": true}'
     expected_status: [201]
```