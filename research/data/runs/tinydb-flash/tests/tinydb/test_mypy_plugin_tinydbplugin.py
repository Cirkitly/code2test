import pytest
from mypy.nodes import MemberExpr, NameExpr
from mypy.options import Options
from tinydb.mypy_plugin import TinyDBPlugin

@pytest.fixture
def mocker():
    """Minimal stand-in for pytest-mock: MagicMock construction plus auto-cleaned patching."""
    from unittest import mock

    class _Mocker:
        def __init__(self):
            self._patchers = []

        # Anything not defined here (MagicMock, Mock, call, ...) comes from unittest.mock.
        def __getattr__(self, name):
            return getattr(mock, name)

        def patch(self, target, *args, **kwargs):
            patcher = mock.patch(target, *args, **kwargs)
            self._patchers.append(patcher)
            return patcher.start()

        def stopall(self):
            while self._patchers:
                self._patchers.pop().stop()

    m = _Mocker()
    try:
        yield m
    finally:
        m.stopall()


@pytest.fixture
def stub_options():
    """A real mypy run Options: Plugin.__init__ rejects anything else at runtime."""
    return Options()


@pytest.fixture
def make_ctx(mocker):
    """Factory returning (ctx, base_fullname) with ctx.call.args holding a NameExpr base class."""
    def factory(class_name, base_fullname):
        klass = NameExpr(base_fullname.rsplit('.', 1)[-1])
        klass.fullname = base_fullname

        ctx = mocker.MagicMock()
        ctx.call.args = [klass]
        ctx.name = class_name
        return ctx, base_fullname

    return factory

def test_get_dynamic_class_hook_returns_callable_for_with_typehint(stub_options):
    plugin = TinyDBPlugin(stub_options)

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    assert callable(hook)

@pytest.mark.parametrize(
    'fullname',
    [
        'tinydb.table.Table',
        'tinydb.utils',
        'tinydb.utils.with_typehints',
        'with_typehint',
        'some.other.module.with_typehint',
        'builtins.dict',
        '',
    ],
)
def test_get_dynamic_class_hook_returns_none_for_other_names(stub_options, fullname):
    plugin = TinyDBPlugin(stub_options)

    assert plugin.get_dynamic_class_hook(fullname) is None

def test_hook_raises_index_error_when_called_without_arguments(stub_options, mocker):
    plugin = TinyDBPlugin(stub_options)

    hook = plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    assert callable(hook)

    ctx = mocker.MagicMock()
    ctx.call.args = []

    with pytest.raises(IndexError):
        hook(ctx)

    ctx.api.add_symbol_table_node.assert_not_called()

import pytest

from mypy.options import Options

from tinydb.mypy_plugin import TinyDBPlugin


def test_plugin_can_be_constructed_with_real_mypy_options():
    """TinyDBPlugin accepts a real mypy Options object and forwards it to Plugin."""
    plugin = TinyDBPlugin(Options())

    assert isinstance(plugin, TinyDBPlugin)
    assert callable(plugin.get_dynamic_class_hook)
    assert plugin.named_placeholders == {}
