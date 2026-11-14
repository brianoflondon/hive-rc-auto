from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hive-rc-auto")
except PackageNotFoundError:
    __version__ = "0.0.0"
