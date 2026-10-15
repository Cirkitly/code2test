import pytest
from mypy.options import Options
from mypy.plugin import Plugin
from tinydb.mypy_plugin import plugin, TinyDBPlugin

def test_plugin_returns_tinydb_plugin_class():
    """The plugin entry point must return the TinyDBPlugin class.

    mypy expects the entry point to hand back the *class* (it is responsible
    for instantiating it with Options), so identity is what matters here.
    """
    assert plugin('1.0') is TinyDBPlugin

def test_plugin_result_is_a_class_not_an_instance():
    """The returned object must be a class so that mypy can instantiate it.

    If an instance were returned, mypy's ``options.plugin(plugin_path)`` would
    fail when calling it with Options.  ``isinstance(result, type)`` is the
    safe structural check for that.
    """
    result = plugin('1.0')

    assert isinstance(result, type), 'plugin() should return a class, not an instance'

def test_plugin_result_subclasses_mypy_plugin_base_class():
    """The returned class must be a subclass of mypy's Plugin base class.

    This ties the entry point to mypy's public plugin interface: whatever
    ``plugin()`` returns has to be usable wherever ``Plugin`` is expected.
    """
    assert issubclass(plugin('1.0'), Plugin)

def test_plugin_ignores_the_version_argument():
    """The ``_version`` argument is unused, so any value yields the same class.

    The underscore prefix signals it is intentionally ignored; this test pins
    that contract so a future change that validates the version will be caught.
    """
    assert plugin('0.1') is plugin('4.2.0') is plugin('') is plugin('anything')

def test_plugin_can_be_instantiated_with_options_like_mypy_does():
    """End-to-end check of the contract mypy relies on.

    mypy calls ``plugin(version)`` and then instantiates the result with an
    ``Options`` instance, which must yield an object exposing
    ``get_dynamic_class_hook`` (used for the ``Table`` dynamic class).
    """
    plugin_class = plugin('1.0')
    instance = plugin_class(Options())

    assert isinstance(instance, Plugin)
    assert callable(instance.get_dynamic_class_hook)

def test_plugin_requires_exactly_one_positional_argument():
    """Omitting the required version argument is a programming error.

    ``plugin`` takes exactly one positional parameter, so calling it with no
    arguments must raise ``TypeError``.
    """
    with pytest.raises(TypeError):
        plugin()

def test_plugin_rejects_extra_positional_arguments():
    """The entry point accepts a single argument only.

    ``plugin`` has no ``*args``, so a second positional argument is a
    ``TypeError`` rather than being silently ignored.
    """
    with pytest.raises(TypeError):
        plugin('1.0', 'extra')

def test_plugin_returned_class_is_stable_across_calls():
    """Repeated invocations must not create a new class each time.

    Returning a freshly created class on every call would break mypy's
    ``issubclass``/identity checks and any user code comparing the plugin type,
    so the result has to be the very same object.
    """
    first = plugin('1.0')
    second = plugin('1.0')

    assert first is second
    assert first is TinyDBPlugin

def test_plugin_result_exposes_get_dynamic_class_hook():
    """The returned class must declare ``get_dynamic_class_hook``.

    That hook is what turns ``Table`` (used as a dynamic class definition)
    into a real class at type-check time, so its presence on the class is the
    observable public behaviour of this entry point.
    """
    assert hasattr(plugin('1.0'), 'get_dynamic_class_hook')
