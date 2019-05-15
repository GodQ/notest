from notest.lib.utils import templated_var
import time

'''
- operation:
    - type: "sleep_operation"
    - seconds: 5
'''


def sleep_operation(config, context=None):
    print("Run sleep_operation")
    assert isinstance(config, dict)
    assert "seconds" in config
    s = config['seconds']
    s = templated_var(s, context)
    print("Sleep {} s".format(s))
    time.sleep(int(s))
    print()


OPERATIONS = {'sleep_operation': sleep_operation}
