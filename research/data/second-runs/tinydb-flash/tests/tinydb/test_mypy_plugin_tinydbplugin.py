import pytest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
import mypy.nodes as mypy_nodes
from mypy.nodes import ArgKind, CallExpr, MemberExpr, NameExpr, StrExpr
from mypy.options import Options
from mypy.plugin import DynamicClassDefContext, Plugin
from tinydb.mypy_plugin import TinyDBPlugin
from tinydb.mypy_plugin import plugin

# --- helpers ----------------------------------------------------------------

def name_expr(name: str, fullname: Optional[str]) -> NameExpr:
    """Build a ``NameExpr`` the way mypy's semantic analyzer would.

    ``fullname`` is what the analyzer fills in once the name has been resolved
    to a module-level definition; it is ``None`` for unresolved local names.
    """
    expr = NameExpr(name)
    expr.fullname = fullname
    return expr


def union_expr(items: List[Any]) -> Any:
    """Build a node standing in for a union expression (``A | B``).

    ``UnionExpr`` is not exported by every mypy release, so fall back to a
    tuple expression and finally to a plain object.  All variants are *not*
    ``NameExpr`` instances, which is what the hook has to reject.
    """
    for cls_name in ('UnionExpr', 'TupleExpr'):
        cls = getattr(mypy_nodes, cls_name, None)
        if cls is None:
            continue
        try:
            return cls(list(items))
        except TypeError:  # pragma: no cover - depends on installed mypy version
            continue
    return SimpleNamespace(items=list(items))


def make_call_expr(args: List[Any]) -> Any:
    """Build a call expression whose positional arguments are ``args``."""
    callee = NameExpr('with_typehint')
    try:
        return CallExpr(callee, list(args), [ArgKind.ARG_POS] * len(args))
    except TypeError:  # pragma: no cover - depends on installed mypy version
        return SimpleNamespace(callee=callee, args=list(args))


def make_dynamic_class_def_context(call: Any, api: Any, name: str, info: Any = None) -> Any:
    """Build a ``DynamicClassDefContext`` for a dynamic class definition.

    ``DynamicClassDefContext`` is a plain data holder whose constructor
    signature varies across mypy releases (field order changed, and some
    versions provide a custom ``__new__``), so try the known spellings first
    and, as a last resort, allocate the real mypy type without running its
    constructor.  The tests therefore never depend on one call convention.
    """
    attrs: Dict[str, Any] = {'call': call, 'name': name, 'api': api, 'info': info}

    attempts = [
        lambda: DynamicClassDefContext(**attrs),
        lambda: DynamicClassDefContext(call, name, api, info),
        lambda: DynamicClassDefContext(call, name, api),
    ]

    for attempt in attempts:
        try:
            ctx = attempt()
        except TypeError:  # pragma: no cover - depends on installed mypy version
            continue
        for key, value in attrs.items():
            try:
                object.__setattr__(ctx, key, value)
            except (AttributeError, TypeError):  # pragma: no cover - read-only field
                pass
        return ctx

    # Fall back to instantiating without the constructor: keeps the genuine
    # mypy class while skipping whichever __init__/__new__ pair we could not
    # satisfy above.
    ctx = object.__new__(DynamicClassDefContext)
    for key, value in attrs.items():
        object.__setattr__(ctx, key, value)
    return ctx


class RecordingApi:
    """Minimal stand-in for mypy's ``SemanticAnalyzerPluginInterface``.

    It records every symbol table insertion requested by the plugin so tests
    can assert on the exact ``(name, fullname)`` pairs that were bound.
    """

    def __init__(self) -> None:
        self.added_nodes: List[Tuple[str, str]] = []

    def add_symbol_table_node(self, name: str, fullname: str) -> None:
        self.added_nodes.append((name, fullname))

    @property
    def names(self) -> List[str]:
        return [name for name, _ in self.added_nodes]

    @property
    def fullnames(self) -> List[str]:
        return [fullname for _, fullname in self.added_nodes]


class SymbolResolver:
    """Stub for ``Plugin.lookup_fully_qualified``.

    The real implementation walks mypy's symbol table of a fully built
    ``MypyFile`` (and asserts that ``set_modules`` was called), which is not
    available in a unit test, so this stub records the requested names and
    answers from an explicit lookup table.
    """

    def __init__(self) -> None:
        self.table: Dict[str, str] = {}
        self.requested: List[str] = []

    def __call__(self, fullname: str) -> Optional[str]:
        self.requested.append(fullname)
        return self.table.get(fullname)


# --- fixtures ---------------------------------------------------------------

@pytest.fixture
def options() -> Options:
    """A default mypy ``Options`` object, as a type checker would supply."""
    return Options()


@pytest.fixture
def tinydb_plugin(options: Options) -> TinyDBPlugin:
    """A freshly constructed plugin instance."""
    return TinyDBPlugin(options)


@pytest.fixture
def resolver(monkeypatch) -> SymbolResolver:
    """Replace mypy's symbol table lookup with a recording stub."""
    stub = SymbolResolver()
    monkeypatch.setattr(Plugin, 'lookup_fully_qualified', stub)
    return stub


@pytest.fixture
def make_context():
    """Factory building ``(ctx, api)`` pairs for dynamic class definitions.

    Defaults to ``Document = with_typehint(Dict)`` where ``Dict`` resolves to
    ``typing.Dict``.
    """
    def factory(name: str = 'Document', args: Optional[List[Any]] = None):
        if args is None:
            args = [name_expr('Dict', 'typing.Dict')]
        api = RecordingApi()
        call = make_call_expr(args)
        return make_dynamic_class_def_context(call, api, name), api

    return factory

def test_get_dynamic_class_hook_returns_callable_for_with_typehint(tinydb_plugin):
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    assert hook is not None
    assert callable(hook)

@pytest.mark.parametrize('fullname', [
    '',
    'with_typehint',
    'tinydb.utils',
    'tinydb',
    'tinydb.utils.with_typehints',
    'tinydb.utils.with_typehint.Inner',
    'typing.Dict',
    'other.plugin',
])
def test_get_dynamic_class_hook_returns_none_for_unrelated_names(tinydb_plugin, fullname):
    assert tinydb_plugin.get_dynamic_class_hook(fullname) is None

def test_hook_target_matches_the_real_with_typehint_helper(tinydb_plugin):
    from tinydb.utils import with_typehint

    real_fullname = '{}.{}'.format(with_typehint.__module__, with_typehint.__qualname__)

    assert real_fullname == 'tinydb.utils.with_typehint'
    assert tinydb_plugin.get_dynamic_class_hook(real_fullname) is not None

def test_constructor_stores_the_given_options(tinydb_plugin, options):
    assert tinydb_plugin.options is options

def test_constructor_initialises_empty_named_placeholders_mapping(tinydb_plugin):
    assert isinstance(tinydb_plugin.named_placeholders, dict)
    assert tinydb_plugin.named_placeholders == {}

def test_named_placeholders_is_not_shared_between_instances(options):
    first = TinyDBPlugin(options)
    second = TinyDBPlugin(options)

    first.named_placeholders['tinydb.utils.with_typehint'] = 'Document'

    assert second.named_placeholders == {}

def test_hook_binds_alias_name_to_resolved_generic_type(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[name_expr('Dict', 'typing.Dict')])

    hook(ctx)

    assert api.added_nodes == [('Document', 'typing.Dict')]

def test_hook_returns_none_while_still_mutating_the_symbol_table(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[name_expr('Dict', 'typing.Dict')])

    result = hook(ctx)

    assert result is None
    assert api.added_nodes == [('Document', 'typing.Dict')]

def test_hook_resolves_the_fullname_of_the_first_argument_once(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[name_expr('Dict', 'typing.Dict')])

    hook(ctx)

    assert resolver.requested == ['typing.Dict']
    assert len(api.added_nodes) == 1

def test_hook_uses_the_name_taken_from_the_context_not_the_expression(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='MyDocumentAlias', args=[name_expr('Dict', 'typing.Dict')])

    hook(ctx)

    assert api.names == ['MyDocumentAlias']
    assert api.fullnames == ['typing.Dict']

def test_hook_binds_the_qualified_name_returned_by_lookup_verbatim(tinydb_plugin, resolver, make_context):
    resolver.table['tinydb.utils.helpers.DictLike'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Alias', args=[name_expr('DictLike', 'tinydb.utils.helpers.DictLike')])

    hook(ctx)

    assert api.added_nodes == [('Alias', 'typing.Dict')]

def test_hook_supports_plain_classes_as_type_arguments(tinydb_plugin, resolver, make_context):
    resolver.table['tinydb.table.Table'] = 'tinydb.table.Table'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='TableAlias', args=[name_expr('Table', 'tinydb.table.Table')])

    hook(ctx)

    assert api.added_nodes == [('TableAlias', 'tinydb.table.Table')]

def test_hook_ignores_additional_arguments(tinydb_plugin, resolver, make_context):
    resolver.table['typing.List'] = 'typing.List'
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(
        name='DocumentList',
        args=[name_expr('List', 'typing.List'), name_expr('Dict', 'typing.Dict')],
    )

    hook(ctx)

    assert resolver.requested == ['typing.List']
    assert api.added_nodes == [('DocumentList', 'typing.List')]

def test_hook_can_bind_several_aliases_in_one_session(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    resolver.table['typing.List'] = 'typing.List'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')

    dict_ctx, dict_api = make_context(name='Document', args=[name_expr('Dict', 'typing.Dict')])
    list_ctx, list_api = make_context(name='DocumentList', args=[name_expr('List', 'typing.List')])
    hook(dict_ctx)
    hook(list_ctx)

    assert dict_api.added_nodes == [('Document', 'typing.Dict')]
    assert list_api.added_nodes == [('DocumentList', 'typing.List')]

def test_hook_leaves_the_named_placeholders_cache_untouched(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[name_expr('Dict', 'typing.Dict')])

    hook(ctx)

    assert api.added_nodes == [('Document', 'typing.Dict')]
    assert tinydb_plugin.named_placeholders == {}

def test_hook_asserts_when_name_expression_has_no_fullname(tinydb_plugin, resolver, make_context):
    resolver.table['typing.Dict'] = 'typing.Dict'
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[name_expr('Dict', None)])

    with pytest.raises(AssertionError):
        hook(ctx)

    assert resolver.requested == []
    assert api.added_nodes == []

def test_hook_asserts_when_the_name_cannot_be_resolved(tinydb_plugin, resolver, make_context):
    # resolver.table is intentionally empty -> lookup_fully_qualified returns None
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[name_expr('Dict', 'typing.Dict')])

    with pytest.raises(AssertionError):
        hook(ctx)

    assert resolver.requested == ['typing.Dict']
    assert api.added_nodes == []

def test_hook_raises_index_error_when_called_without_arguments(tinydb_plugin, resolver, make_context):
    hook = tinydb_plugin.get_dynamic_class_hook('tinydb.utils.with_typehint')
    ctx, api = make_context(name='Document', args=[])

    with pytest.raises(IndexError):
        hook(ctx)

    assert api.added_nodes == []

def test_plugin_entry_point_exposes_the_with_typehint_hook(options):
    candidate = plugin('4.8.0')
    plugin_class = candidate if isinstance(candidate, type) else candidate()

    assert issubclass(plugin_class, Plugin)

    instance = plugin_class(options)
    assert instance.get_dynamic_class_hook('tinydb.utils.with_typehint') is not None
    assert instance.get_dynamic_class_hook('something.else') is None
