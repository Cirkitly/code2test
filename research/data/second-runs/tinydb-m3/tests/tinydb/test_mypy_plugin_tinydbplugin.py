import pytest
from mypy.nodes import NameExpr
from mypy.options import Options
from mypy.plugin import Plugin, DynamicClassDefContext
from tinydb.mypy_plugin import TinyDBPlugin

@pytest.fixture
def options() -> Options:
    """A fresh default mypy ``Options`` instance suitable for plugin construction."""
    return Options()


@pytest.fixture
def plugin(options) -> TinyDBPlugin:
    """A vanilla ``TinyDBPlugin`` built on the ``options`` fixture."""
    return TinyDBPlugin(options)


# --- Test doubles ---------------------------------------------------------

class _StubSymbolTableNode:
    """Sentinel stand-in for a mypy SymbolTableNode."""


class _RecordingAPI:
    """Captures calls to ``add_symbol_table_node`` for later assertions."""

    def __init__(self) -> None:
        self.calls = []

    def add_symbol_table_node(self, name, node) -> None:
        self.calls.append((name, node))


class _StubCall:
    """Provides only the ``.args`` attribute that the plugin accesses."""

    def __init__(self, args) -> None:
        self.args = list(args)


class _StubClassDef:
    """Stand-in for a ClassDef node; the plugin does not touch it."""


class _ControllablePlugin(TinyDBPlugin):
    """Subclass that overrides ``lookup_fully_qualified`` for test control.

    Records every lookup so tests can assert that the inherited lookup is
    invoked with the expected fully-qualified name.
    """

    def __init__(self, options: Options, lookup_result) -> None:
        super().__init__(options)
        self._lookup_result = lookup_result
        self.lookup_calls = []

    def lookup_fully_qualified(self, fullname: str):
        self.lookup_calls.append(fullname)
        return self._lookup_result


# --- Helper ---------------------------------------------------------------

def _make_context(api, args, name: str = "AliasedClass") -> DynamicClassDefContext:
    """Construct a ``DynamicClassDefContext`` carrying the given api and decorator args."""
    return DynamicClassDefContext(
        api=api,
        name=name,
        _cls=_StubClassDef(),
        reason="with_typehint",
        call=_StubCall(args),
    )

def test_init_seeds_named_placeholders_as_empty_dict(plugin):
    assert plugin.named_placeholders == {}
    assert isinstance(plugin.named_placeholders, dict)


def test_init_accepts_mypy_options_instance(options):
    p = TinyDBPlugin(options)
    assert isinstance(p, Plugin)
    assert p.named_placeholders == {}


def test_named_placeholders_is_per_instance_state(options):
    a = TinyDBPlugin(options)
    b = TinyDBPlugin(options)
    a.named_placeholders["foo"] = "bar"
    assert b.named_placeholders == {}


def test_get_dynamic_class_hook_returns_none_for_unrelated_fullname(plugin):
    assert plugin.get_dynamic_class_hook("module.other") is None
    assert plugin.get_dynamic_class_hook("tinydb.utils.something_else") is None
    assert plugin.get_dynamic_class_hook("") is None


def test_get_dynamic_class_hook_returns_callable_for_with_typehint(plugin):
    hook = plugin.get_dynamic_class_hook("tinydb.utils.with_typehint")
    assert hook is not None
    assert callable(hook)


def test_get_dynamic_class_hook_fullname_match_is_exact(plugin):
    assert plugin.get_dynamic_class_hook("tinydb.utils.with_typehint_extra") is None
    assert plugin.get_dynamic_class_hook(
        "elsewhere.tinydb.utils.with_typehint"
    ) is None
    # Sanity: the exact fullname still matches.
    matched = plugin.get_dynamic_class_hook("tinydb.utils.with_typehint")
    assert matched is not None

