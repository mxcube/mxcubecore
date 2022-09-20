try:
    # Python3.8+ standard library
    from importlib.metadata import metadata
except ImportError:
    # Python3.7 module backport
    import importlib_metadata as metadata

__version__ = metadata.version(__package__ or __name__)
