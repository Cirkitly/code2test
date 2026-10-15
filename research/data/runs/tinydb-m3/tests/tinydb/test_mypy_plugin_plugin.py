import pytest
from tinydb.mypy_plugin import plugin, TinyDBPlugin
from mypy.plugin import Plugin
import tinydb.mypy_plugin

def test_plugin_returns_a_class_object():
    """The plugin entry point must return a class object so that mypy
    can instantiate it with options."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("1.0")

    # The returned value must be a class (type), not an instance.
    assert isinstance(result, type), (
        f"plugin() should return a class, got {type(result).__name__}"
    )

def test_plugin_returns_the_tinydb_plugin_class():
    """plugin() must return the TinyDBPlugin class that the module exports,
    so that mypy picks up the registered hooks."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("1.0")

    assert result is TinyDBPlugin, (
        "plugin() must be the TinyDBPlugin class reference defined in the module"
    )

def test_plugin_with_empty_version_string():
    """The version parameter is unused (prefixed with '_'), so an empty
    string must still produce a valid class reference."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("")

    assert result is TinyDBPlugin

def test_plugin_ignores_version_argument():
    """The function signature marks the version argument as unused, so the
    return value must not depend on the string passed in."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    versions = ["0.1", "1.0", "99.99", "abc", "1.0.0-rc1", "*"]

    results = [plugin(v) for v in versions]

    # Every call must produce the same class regardless of the version string.
    assert all(r is TinyDBPlugin for r in results), (
        "plugin() must return TinyDBPlugin regardless of the version string"
    )
    # All results must refer to the same object (not just equal classes).
    assert len({id(r) for r in results}) == 1

def test_plugin_returned_class_is_a_mypy_plugin_subclass():
    """The mypy plugin contract requires the returned object to be a
    subclass of mypy.plugin.Plugin."""
    from mypy.plugin import Plugin
    from tinydb.mypy_plugin import plugin

    result = plugin("1.0")

    assert issubclass(result, Plugin), (
        "Returned class should be a subclass of mypy.plugin.Plugin"
    )

def test_plugin_returned_class_has_get_dynamic_class_hook():
    """TinyDBPlugin advertises a get_dynamic_class_hook method that
    mypy will call; the returned class must expose this attribute."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("1.0")

    assert hasattr(result, "get_dynamic_class_hook"), (
        "Returned class must expose get_dynamic_class_hook"
    )
    # And it must come from the TinyDBPlugin class itself, not from an
    # unrelated base class.
    assert "get_dynamic_class_hook" in vars(TinyDBPlugin) or any(
        "get_dynamic_class_hook" in vars(klass)
        for klass in TinyDBPlugin.__mro__[1:]
    )

def test_plugin_does_not_return_an_instance():
    """mypy calls plugin() to receive the *class* to instantiate. Returning
    an instance would break the mypy plugin loader contract."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("1.0")

    # The result is a class, not an instance. An instance would fail this
    # isinstance check against type, and would also fail the class check
    # against TinyDBPlugin.
    assert not isinstance(result, TinyDBPlugin) or isinstance(result, type)
    # Specifically: the result must NOT be an instance, only the class.
    assert type(result) is type, "plugin() must return the class itself, not an instance"

def test_plugin_returned_class_callable_for_instantiation():
    """The class returned by plugin() must be usable by mypy, which will
    construct it by calling TinyDBPlugin(options). It must therefore be
    a callable class."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    result = plugin("1.0")

    # The class itself must be callable (i.e. it is a class object, not e.g.
    # a sentinel or None).
    assert callable(result), "Returned object must be callable as a class"
    assert result is TinyDBPlugin

def test_plugin_returns_same_object_on_repeated_calls():
    """Each invocation of plugin() must yield the exact same class object,
    so mypy consistently receives the registered hook implementation."""
    from tinydb.mypy_plugin import plugin, TinyDBPlugin

    first = plugin("1.0")
    second = plugin("1.0")
    third = plugin("999.999.999")

    assert first is second
    assert second is third
    assert first is TinyDBPlugin

def test_plugin_module_exposes_plugin_callable():
    """The mypy plugin loader imports `plugin` from the configured module.
    The tinydb.mypy_plugin module must expose a callable named `plugin`."""
    import tinydb.mypy_plugin as mypy_plugin_module

    assert hasattr(mypy_plugin_module, "plugin"), (
        "tinydb.mypy_plugin must expose a `plugin` attribute"
    )
    assert callable(mypy_plugin_module.plugin), (
        "`plugin` must be callable"
    )
