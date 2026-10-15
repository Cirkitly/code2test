import pytest
from tinydb.mypy_plugin import plugin
from tinydb.mypy_plugin import TinyDBPlugin
from mypy.options import Options
from mypy.plugin import Plugin

"""The TinyDBPlugin class as returned by the plugin entry point (mypy version 1.0.0)."""


@pytest.fixture
def tiny_db_plugin_class():
    return plugin('1.0.0')

"""A default mypy Options object, as required by TinyDBPlugin.__init__."""


@pytest.fixture
def mypy_options():
    return Options()

def test_plugin_returns_tiny_db_plugin_class():
    """The mypy entry point must return the TinyDBPlugin class itself."""
    result = plugin('1.0.0')

    assert result is TinyDBPlugin

def test_plugin_returns_a_class_not_an_instance():
    """mypy expects a *class* from the entry point so it can instantiate it itself."""
    result = plugin('1.0.0')

    assert isinstance(result, type)
    assert not isinstance(result, Plugin)

def test_plugin_result_is_a_mypy_plugin_subclass(tiny_db_plugin_class):
    """The returned class must be usable as a mypy plugin."""
    assert issubclass(tiny_db_plugin_class, Plugin)
    assert callable(getattr(tiny_db_plugin_class, 'get_dynamic_class_hook', None))

@pytest.mark.parametrize('version', [
    '1.0.0',
    '0.1',
    '4.8.3',
    '',
    'not-a-version',
    '1.0.0-beta.1+build.42',
])
def test_plugin_ignores_the_version_argument(version):
    """The version parameter is unused, so every value maps to the same plugin class."""
    assert plugin(version) is TinyDBPlugin

@pytest.mark.parametrize('version', [None, 1, 3.5, object()])
def test_plugin_does_not_validate_non_string_versions(version):
    """No type checking happens on the version argument -- nothing is raised."""
    assert plugin(version) is TinyDBPlugin

def test_plugin_is_stable_across_calls():
    """Repeated invocations must return the very same class object."""
    first = plugin('1.0.0')
    second = plugin('2.0.0')
    third = plugin('1.0.0')

    assert first is second is third

def test_plugin_accepts_version_as_keyword_argument():
    """The parameter is named ``_version`` and can be passed by keyword."""
    assert plugin(_version='1.0.0') is TinyDBPlugin

def test_plugin_result_can_be_instantiated_with_options(tiny_db_plugin_class, mypy_options):
    """mypy instantiates the returned class with its Options object."""
    instance = tiny_db_plugin_class(mypy_options)

    assert isinstance(instance, Plugin)
    assert isinstance(instance, TinyDBPlugin)
    assert callable(instance.get_dynamic_class_hook)

def test_plugin_instance_dynamic_class_hook_returns_hook_or_none(
        tiny_db_plugin_class, mypy_options):
    """Hook lookup for any class name yields either None or a callable."""
    instance = tiny_db_plugin_class(mypy_options)

    hook = instance.get_dynamic_class_hook('tinydb.table.Table')

    assert hook is None or callable(hook)

def test_plugin_requires_exactly_one_argument():
    """Error condition: the version argument is mandatory and unique."""
    with pytest.raises(TypeError):
        plugin()

    with pytest.raises(TypeError):
        plugin('1.0.0', '2.0.0')
