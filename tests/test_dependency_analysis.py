"""Tests for the Python code analyzer, dependency graph building and ordering."""

from code2test.src.be.dependency_analyzer import DependencyGraphBuilder
from code2test.src.be.dependency_analyzer.analyzers.python import analyze_python_file
from code2test.src.be.dependency_analyzer.topo_sort import (
    build_graph_from_components,
    detect_cycles,
    resolve_cycles,
    topological_sort,
)
from code2test.src.config import Config

SHOP = '''
"""Shopping cart helpers."""


def total(items):
    """Sum item prices after discount."""
    return sum(discount(i.price) for i in items)


def discount(price: float) -> float:
    return price * 0.9


class Item:
    """An item in the cart."""

    def __init__(self, price):
        self.price = price

    def doubled(self):
        return Item(self.price * 2)


class SpecialItem(Item):
    pass


def _private_helper():
    return total([])
'''


def analyze(content=SHOP, path="/repo/shop/cart.py"):
    return analyze_python_file(path, content, repo_path="/repo")


def test_top_level_functions_and_classes_become_components():
    nodes, _ = analyze()
    by_id = {n.id: n for n in nodes}
    assert set(by_id) == {"shop.cart.total", "shop.cart.discount", "shop.cart.Item",
                          "shop.cart.SpecialItem", "shop.cart._private_helper"}
    total = by_id["shop.cart.total"]
    assert total.component_type == "function"
    assert total.relative_path == "shop/cart.py"
    assert total.docstring == "Sum item prices after discount."
    assert total.source_code.startswith("def total(items):")
    assert total.parameters == ["items"]
    assert by_id["shop.cart.SpecialItem"].base_classes == ["Item"]
    # methods are part of their class, not separate components
    assert "def doubled" in by_id["shop.cart.Item"].source_code


def test_call_to_function_defined_later_is_resolved():
    _, relationships = analyze()
    edges = {(r.caller, r.callee) for r in relationships if r.is_resolved}
    assert ("shop.cart.total", "shop.cart.discount") in edges


def test_builtins_are_not_dependencies():
    _, relationships = analyze()
    assert not any(r.callee in ("sum", "shop.cart.sum") for r in relationships)


def test_inheritance_and_class_internal_calls_are_edges():
    _, relationships = analyze()
    edges = {(r.caller, r.callee) for r in relationships if r.is_resolved}
    assert ("shop.cart.SpecialItem", "shop.cart.Item") in edges
    assert ("shop.cart.Item", "shop.cart.Item") in edges  # doubled() builds an Item


def test_syntax_error_yields_no_components():
    nodes, relationships = analyze("def broken(:\n")
    assert nodes == [] and relationships == []


def test_graph_builder_links_dependencies_across_the_repo(tmp_path):
    (tmp_path / "shop").mkdir()
    (tmp_path / "shop" / "__init__.py").write_text("")
    (tmp_path / "shop" / "cart.py").write_text(SHOP)
    config = Config(
        repo_path=str(tmp_path), output_dir=str(tmp_path / "out"),
        dependency_graph_dir=str(tmp_path / "out"), docs_dir=str(tmp_path / "out"),
        max_depth=2, llm_base_url="", llm_api_key="", main_model="", cluster_model="",
    )
    components, _ = DependencyGraphBuilder(config).build_dependency_graph()
    assert "shop.cart.discount" in components["shop.cart.total"].depends_on

    order = topological_sort(build_graph_from_components(components))
    assert order.index("shop.cart.discount") < order.index("shop.cart.total")


def test_topological_sort_puts_dependencies_first():
    graph = {"app": {"service"}, "service": {"db", "cache"}, "db": set(), "cache": set()}
    order = topological_sort(graph)
    assert order.index("db") < order.index("service") < order.index("app")
    assert order.index("cache") < order.index("service")
    assert sorted(order) == sorted(graph)


def test_cycles_are_detected_and_broken():
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}}
    cycles = detect_cycles(graph)
    assert any(sorted(c) == ["a", "b", "c"] for c in cycles)

    acyclic = resolve_cycles(graph)
    assert detect_cycles(acyclic) == []
    assert set(acyclic) == set(graph)
    order = topological_sort(graph)  # must terminate and include every node once
    assert sorted(order) == ["a", "b", "c", "d"]
