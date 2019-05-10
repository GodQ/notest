# Plugin Development

NoTest插件机制保留了pyresttest的格式，因此可以直接原生使用其已实现的插件，故该部分直接引用了原版文档。

# Extensions
NoTest provides hooks for extending built-in components with your own Python code.  

# What Can An Extension Do?

- In general: use more advanced dependencies while not making them required for installation
- Generators: generate data for templating URL/request body/tests/etc
- Extractors: get data from HTTP response body/headers and use it in future tests
- Validators: write custom tests using headers & response bodies
- Test Functions: for the ExtractTest validator, validate a single condition
- Comparator functions: for the ComparatorValidator, compare expected and actual values

## How to load user plugins?
```bash
notest a.yaml --ext-dir my_plugin_dir
```

## What does an extension look like?
```python
import pyresttest.validators as validators

# Define a simple generator that doubles with each value
def parse_generator_doubling(config):

    start = 1
    if 'start' in config:
        start = int(config['start'])

    # We cannot simply use start as the variable, because of scoping limitations
    def generator():
        val = start
        while(True):
            yield val
            val = val*2
    return generator()

GENERATORS = {'doubling': parse_generator_doubling}
```

If this is imported when executing the test, you can now use this generator in tests. 

# Full Example
See the [sample extension](sample_extension.py).  
It shows an extension for all extensible functions. 


# What Doe An Extension Need To Work?

1. Function(s) to run 
2. Registry Entries: these are special ALLCAPS variables binding extension names

## Functions (different for each type)

### Test Functions
These are the simplest, one-argument functions that return True or False
```python
def test(x):
    return x in [1, 2, 3]
```

### Comparator Functions
Compare two values and return True/False
```python
def compare(a, b):
    return a > b
```

### Generators 
These are [standard python generators](https://wiki.python.org/moin/Generators).
There is ONE twist, they should be infinite (for benchmark use).

The function takes one argument, config, which is a string or dictionary of arguments for creating the generator. 

```python 
def factory_choice_generator(values):
    """ Return a generator that picks values from a list randomly """

    def choice_generator():
        my_list = list(values)
        rand = random.Random()
        while(True):
            yield random.choice(my_list)
    return choice_generator

def parse_choice_generator(config):
    """ Parse choice generator """
    vals = config['values']
    if not vals:
        raise ValueError('Values for choice sequence must exist')
    if not isinstance(vals,list):
        raise ValueError('Values must be a list of entries')
    return factory_choice_generator(vals)()
```

**The function for the registry would be ```parse_choice_generator```**

### Extractors (Now things get a bit more complex)
These need to be objects, and should extend pyresttest.AbstractExtractor
The 'parse' function below will be registered in the registry. 

Example:
```python
class HeaderExtractor(AbstractExtractor):
    """ Extractor that pulls out a named header """
    extractor_type = 'header'  # Printable name for the type
    is_header_extractor = True  # Use headers in extraction
    is_body_extractor = False  # Uses body in extraction

    def extract_internal(self, body=None, headers=None, context=None):
        """ The real logic, extract a value, using a templated query string and args
            The query is an attribute stored in the parent, and templating is used
        """
        try:
            return headers[self.query]
        except Exception:
            return None

    @classmethod
    def parse(cls, config, extractor_base=None):
        base = HeaderExtractor()
        # Base parser automatically handles templating logic
        # And reads the query
        base.query = config.get('query')
        return base
```

### Validators 
Validators should extend AbstractValidator. 
The parse function below will be registered in the registry VALIDATORS. 

```python
class ExtractTestValidator(AbstractValidator):
    """ Does extract and test from request body """
    name = 'ExtractTestValidator'
    extractor = None
    test_fn = None
    test_name = None
    config = None

    @staticmethod
    def parse(config):
        """ Config is a dict """
        output = ExtractTestValidator()
        config = parsing.lowercase_keys(parsing.flatten_dictionaries(config))
        output.config = config
        extractor = _get_extractor(config)
        output.extractor = extractor

        test_name = config['test']
        output.test_name = test_name
        test_fn = VALIDATOR_TESTS[test_name]
        output.test_fn = test_fn
        return output

    def validate(self, body=None, headers=None, context=None):
        try:
            extracted = self.extractor.extract(body=body, headers=headers, context=context)
        except Exception as e:
            return Failure(message="Exception thrown while running extraction from body", details=e, validator=self)

        tested = self.test_fn(extracted)
        if tested:
            return True
        else:
            failure = Failure(details=self.config, validator=self)
            failure.message = "Extract and test validator failed on test: {0}({1})".format(self.test_name, extracted)
            return failure
```


# Registry
The extension loader will look for special registry variables in the module and attempt to load them. 

Registries are dictionarys of {registered_name: function}. 
Registry names are ALWAYS case-insensitive, since they are keywords for the YAML syntax. 

These are:
- VALIDATOR_TESTS - function is just the test function
- COMPARATORS - function is just the comparison function
- GENERATORS - function is a parse function to get a generator
- EXTRACTORS - function is a parse function returning an AbstractExtractor implementation
- VALIDATORS - function is a parse function returning an AbstractValidator implementation

Each one maps to the same registry in notest.validators. 

# Use Case Suggestions
- **Need to generate complex, formatted data?**  
  - Write a generator extension, or multiple generators may be used together to create a complex result
- **Want to test whether API results fit a business rule?** 
  - Write a validator extension, your logic can be as complex as you like
- **Want to apply a business rule to the output and use the result?** 
  - Write an extractor extension
  - You can do testing with the result via the validators ExtractTest and ComparatorValidator 
  - By declaring the extractor with the test, it can be used in future tests
- **Want to test with complex matching logic between two parts of a response?**
    - Write a Comparator to do the comparison, use extractors for pulling out the components
- **Want to run external logic after a test?**
    - Write a Operation to do the logic, such as change the mysql records
- **Want to interact with an external system (a DB, for example) before tests?**    
    + Write a custom generator function returning data
- **Want to confirm results were written to a database?**
    + Write a custom validator or extractor that speaks to the database
    + An extractor can return a value from the DB for comparison
    + A validator can do the database fetch and return a failure if it was not right


