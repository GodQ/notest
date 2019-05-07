from pyresttest.lib.utils import templated_var

'''
- operation:
    - type: "print_operation"
    - print: 'hello world'
'''

def print_operation(config, context=None):
    print("Run print_operation")
    assert isinstance(config, dict)
    assert "print" in config
    pr = config['print']
    pr = templated_var(pr, context)
    print(pr)
    print('')


OPERATIONS = {'print_operation': print_operation}
