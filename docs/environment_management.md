# Multiple Environment Management

为应对多环境管理，NoTest提供了指定环境文件的功能 
  --env-vars=ENV_VARS   environment variables, format: json, will be injected
                        to config-variable-binds of testset
  --env-file=ENV_FILE   environment variables file, will be injected to
                        config-variable-binds of testset
						
不同的测试环境需要记录在不同的json文件，执行命令或者调用lib时，notest会自动读取环境配置添加到testset的全局变量variable_binds中