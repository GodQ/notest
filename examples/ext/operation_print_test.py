from notest.lib.utils import templated_var

'''
- operation:
    - type: "print_operation_test"
    - print: 'hello world'
'''

def print_operation_test(config, context=None):
    print("Run print_operation_test")
    assert isinstance(config, dict)
    assert "print" in config
    pr = config['print']
    pr = templated_var(pr, context)
    print(pr)
    print('')


OPERATIONS = {'print_operation_test': print_operation_test}
