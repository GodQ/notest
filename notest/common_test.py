
class CommonTest:
    test_type = None
    config = None
    testset_config = None
    group = None

    def run_test(self, test_config, context=None, handler=None, **kwargs):
        raise NotImplementedError()

    def reload(self):
        raise NotImplementedError()
