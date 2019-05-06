from pprint import pprint
import yaml

d = {
    "a": 1,
    "b": {
        "b1": 1,
        "b2": 2
    },
    "c": [
        1, 2, 3
    ],
    "d": [
        {
            "d1": 1,
            "d2": 2
         }
    ]
}

y = """
- test:
    - generator_binds:
        - task_id: task_id
        - name: name
    - group: "Quickstart"
    - name: "post"
    - url: "/tasks"
    - method: "POST"
    - headers: {'Content-Type': 'application/json', "Token": 123}
    - body: {template: '{"title": "$name", "id": $task_id, "done": $done}'}
    - expected_status: [201]
    - validators:
        # Test key does not exist
        - extract_test: {jsonpath_mini: "info.0.title", test: "exists"}
        - compare:
            - jsonpath_mini: "info.0.id"
            - comparator: "str_eq"
            - expected: {template: '$task_id'}
    - extract_binds:
        - post_task_id: {jsonpath_mini: 'info.0.id'}
        - post_task_title:
            mysql:
              sql: 'select name from sites limit 1'
              config: '{"user": "root", "password": "password", "host": "192.168.99.101", "database": "test"}'
"""

# print(yaml.dump(d))
pprint(yaml.load(y))
