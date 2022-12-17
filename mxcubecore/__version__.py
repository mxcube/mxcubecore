try:
    # Python3.8+ standard library
    from importlib.metadata import version
except ImportError:
    # Python3.7 module backport
    from importlib_metadata import version

try:
    __version__ = version(__package__ or __name__)
except:
    __version__ = 'local'

