import pytest
from unittest.mock import MagicMock
from tinydb.mypy_plugin import TinyDBPlugin
from mypy.options import Options
from mypy.nodes import NameExpr

@pytest.fixture
def plugin():
    """Provide a fresh TinyDBPlugin instance for each test."""
    return TinyDBPlugin(Options())

def test_init_initializes_named_placeholders_as_empty_dict():
    """named_placeholders is initialized as an empty Dict[str, str]."""
    p = TinyDBPlugin(Options())
    assert p.named_placeholders == {}
    assert isinstance(p.named_placeholders, dict)


def test_named_placeholders_is_per_instance_state():
    """Each plugin instance owns its own named_placeholders dict (mutable per-run state)."""
    p1 = TinyDBPlugin(Options())
    p2 = TinyDBPlugin(Options())
    p1.named_placeholders['k'] = 'v'
    assert 'k' not in p2.named_placeholders
    assert p2.named_placeholders == {}


def test_get_dynamic_class_hook_returns_callable_for_with_typehint(plugin):
    """get_dynamic_class_hook returns a callable for tinydb.utils.with_typehint."""
    result = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    assert result is not None
    assert callable(result)


def test_get_dynamic_class_hook_returns_none_for_unrelated_names(plugin):
    """get_dynamic_class_hook returns None for any fullname that is not with_typehint."""
    for name in (
        'some.other.module',
        'tinydb.utils',
        'tinydb.utils.with_typehint.sub',   # must be exact match, not prefix
        'tinydb.utils.with_typehintx',      # must be exact match, not prefix
        'with_typehint',                     # not fully qualified
    ):
        assert plugin.get_dynamic_class_hook(name) is None


def test_get_dynamic_class_hook_match_is_case_sensitive(plugin):
    """The fullname comparison is case-sensitive."""
    assert plugin.get_dynamic_class_hook('Tinydb.utils.with_typehint') is None
    assert plugin.get_dynamic_class_hook('TINYDB.UTILS.WITH_TYPEHINT') is None


def test_get_dynamic_class_hook_returns_none_for_empty_string(plugin):
    """get_dynamic_class_hook returns None for an empty fullname."""
    assert plugin.get_dynamic_class_hook('') is None


def test_hook_calls_lookup_with_class_fullname(plugin):
    """The hook passes the NameExpr's fullname into lookup_fully_qualified."""
    plugin.lookup_fully_qualified = MagicMock(return_value='symbol_node')

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    klass = NameExpr('Source')
    klass.fullname = 'pkg.module.Source'

    ctx = MagicMock()
    ctx.call.args = [klass]
    ctx.name = 'New'
    ctx.api.add_symbol_table_node = MagicMock()

    hook(ctx)

    plugin.lookup_fully_qualified.assert_called_once_with('pkg.module.Source')


def test_hook_registers_symbol_table_node_under_dynamic_name(plugin):
    """The hook installs the resolved node under ctx.name via add_symbol_table_node."""
    plugin.lookup_fully_qualified = MagicMock(return_value='qualified_node')

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    klass = NameExpr('MyClass')
    klass.fullname = 'pkg.MyClass'

    ctx = MagicMock()
    ctx.call.args = [klass]
    ctx.name = 'DynamicAlias'
    ctx.api.add_symbol_table_node = MagicMock()

    hook(ctx)

    ctx.api.add_symbol_table_node.assert_called_once_with('DynamicAlias', 'qualified_node')


def test_hook_returns_none(plugin):
    """The hook performs side effects only and returns None."""
    plugin.lookup_fully_qualified = MagicMock(return_value='q')

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    klass = NameExpr('MyClass')
    klass.fullname = 'pkg.MyClass'

    ctx = MagicMock()
    ctx.call.args = [klass]
    ctx.name = 'New'
    ctx.api.add_symbol_table_node = MagicMock()

    assert hook(ctx) is None


def test_hook_raises_assertion_error_when_arg_is_not_name_expr(plugin):
    """First invariant: the first arg must be a NameExpr; else AssertionError."""
    plugin.lookup_fully_qualified = MagicMock(return_value='q')

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    ctx = MagicMock()
    ctx.call.args = ['not_a_name_expr']  # a plain string is not a NameExpr

    with pytest.raises(AssertionError):
        hook(ctx)


def test_hook_raises_assertion_error_when_fullname_is_none(plugin):
    """Second invariant: the referenced class must have a known fullname."""
    plugin.lookup_fully_qualified = MagicMock(return_value='q')

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    klass = NameExpr('Anon')
    klass.fullname = None  # NameExpr's default fullname is None

    ctx = MagicMock()
    ctx.call.args = [klass]

    with pytest.raises(AssertionError):
        hook(ctx)


def test_hook_raises_assertion_error_when_lookup_returns_none(plugin):
    """Third invariant: lookup_fully_qualified must return a non-None node."""
    plugin.lookup_fully_qualified = MagicMock(return_value=None)

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    klass = NameExpr('MyClass')
    klass.fullname = 'pkg.MyClass'

    ctx = MagicMock()
    ctx.call.args = [klass]
    ctx.api.add_symbol_table_node = MagicMock()

    with pytest.raises(AssertionError):
        hook(ctx)


def test_hook_does_not_register_symbol_when_assertion_fails(plugin):
    """On any invariant failure, add_symbol_table_node must not be called."""
    plugin.lookup_fully_qualified = MagicMock(return_value=None)

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    klass = NameExpr('MyClass')
    klass.fullname = 'pkg.MyClass'

    ctx = MagicMock()
    ctx.call.args = [klass]
    ctx.api.add_symbol_table_node = MagicMock()

    with pytest.raises(AssertionError):
        hook(ctx)

    ctx.api.add_symbol_table_node.assert_not_called()
