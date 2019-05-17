# Allow extensions to see root folder
import sys

try:
    import notest
except ImportError:
    sys.path.insert(0, '..')
