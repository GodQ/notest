#Test App Demo

## 被测应用介绍
### 被测应用
在demo项目中，被测应用为target目录下的fake_rest_server.py，该脚本为一个基于python flask的rest api server。其中简单实现了一个任务task创建更新和删除操作，并为了配合autotest一些功能的展示提供了若干个与task无关的api。在此服务中，每个task由唯一id、名称title和完成状态done组成。API如下：
#### POST /token
创建一个token，
简单起见，request不做验证，response body为json格式，如下：
 ```python
{
 "status": "Created",
 "Token": "1234566789vbxgdgd"
 }
```
#### POST /tasks
创建一个或多个task，id为可选字段，如果指定了id就会校验是否已存在，已存在则返回错误，若未指定id则为该task自动分配一个id。request为一个task或者多个task组成的数组：
```python
{
 	"id": 123,
	"title":"aaa",
	"done": false
 }
 或
 [
  {
	"title":"aaa",
	"done": false
 }，
 {
	"title":"bbb",
	"done": false
 }
]
```

#### GET  /tasks
返回所有tasks， response为
```python
[
 {
 	"id": 123,
	"title":"aaa",
	"done": true
 },
 {
 	"id": 123,
	"title":"bbb",
	"done": false
 }
]
```

#### PUT  /task/\<int:task_id\>
更新一个task的字段，若id不存在则报错。
response为该task所有信息：
```python
{
 	"id": 123,
	"title":"aaa",
	"done": false
 }
```

#### GET  /task/\<int:task_id\>
获取该task
response为该task所有信息：
```python
{
 	"id": 123,
	"title":"aaa",
	"done": false
 }
```

#### DELETE /task/\<int:task_id\>
删除一个task
response为该被删除的task所有信息：
```python
{
 "status": "Deleted",
 "info": {
 	"id": 123,
	"title":"aaa",
	"done": false
 }
}
```

#### POST  /echo_request_body
直接返回request的body

#### GET  /get_form_response
直接返回一个form格式的response："param1=1&param2=2"，为了示例autotest对form格式response的解析

#### POST  /tasks_form
接受一个form格式的task，格式为
"title=aaa&done=True"
response为：
```python
{
 "status": "Created",
 "info": {
 	"id": 123,
	"title":"aaa",
	"done": true
 }
}
```

#### POST  /clear_all
删除所有tasks