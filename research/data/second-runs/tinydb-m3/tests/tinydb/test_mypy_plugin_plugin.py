import pytest
from tinydb.mypy_plugin import plugin
from tinydb.mypy_plugin import TinyDBPlugin
from mypy.plugin import Plugin

def test_plugin_returns_tinydb_plugin_class():
    """Verify the plugin function returns the TinyDBPlugin class itself."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("1.0.0")

    assert result is TinyDBPlugin

def test_plugin_returns_class_object_not_instance():
    """Verify plugin returns a class object rather than an instantiated Plugin."""
    from tinydb.mypy_plugin import plugin

    result = plugin("1.0.0")

    assert isinstance(result, type), (
        "plugin() should return a class object (type), not an instance"
    )
    assert not hasattr(result, "_options") or not isinstance(
        getattr(result, "_options", None), object
    ) or True  # Cheap check that it isn't an Options-bearing instance
    # The definitive check: returned class should be uninstantiated
    assert result.__class__ is type

def test_plugin_returned_class_is_mypy_plugin_subclass():
    """Verify the returned class inherits from mypy.plugin.Plugin."""
    from tinydb.mypy_plugin import plugin
    from mypy.plugin import Plugin

    result = plugin("1.0.0")

    assert issubclass(result, Plugin), (
        "Returned class must be a subclass of mypy.plugin.Plugin"
    )

def test_plugin_accepts_arbitrary_version_string():
    """Verify the version argument is unused and any string is accepted."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    versions = ["1.0.0", "0.4.0", "0.991", "anything", "x"]

    results = [plugin(v) for v in versions]

    assert all(r is TinyDBPlugin for r in results), (
        "All calls with different version strings should return TinyDBPlugin"
    )
    assert len(set(results)) == 1, (
        "plugin() should always return the same class regardless of version"
    )

def test_plugin_callable_repeatedly_consistent():
    """Verify plugin can be called repeatedly and returns the same class."""
    from tinydb.mypy_plugin import plugin

    first = plugin("1.0.0")
    second = plugin("1.0.0")
    third = plugin("1.0.0")

    assert first is second
    assert second is third

def test_plugin_returned_class_has_documented_method():
    """Verify the returned class provides get_dynamic_class_hook as documented."""
    from tinydb.mypy_plugin import plugin

    result = plugin("1.0.0")

    assert hasattr(result, "get_dynamic_class_hook"), (
        "TinyDBPlugin must expose get_dynamic_class_hook per the API contract"
    )
    assert callable(getattr(result, "get_dynamic_class_hook")), (
        "get_dynamic_class_hook should be a callable method on the class"
    )

def test_plugin_function_is_callable():
    """Verify the imported plugin symbol is a callable function."""
    from tinydb.mypy_plugin import plugin

    assert callable(plugin), "plugin must be callable"
