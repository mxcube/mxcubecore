try:
    # Python3.8+ standard library
    from importlib.metadata import version
except ImportError:
    # Python3.7 module backport
    from importlib_metadata import version

__version__ = version(__package__ or __name__)
