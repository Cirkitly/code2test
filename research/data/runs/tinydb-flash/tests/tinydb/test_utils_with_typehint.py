import pytest
from tinydb.utils import with_typehint, FrozenDict, LRUCache
from typing import List, Optional, Type, Union

class Bar:
    """A class whose type hints are meant to be transferred to other classes."""

    value: int = 42

    def bar_method(self) -> int:
        return self.value


@pytest.fixture
def hinted_class():
    """Build ``class Foo(with_typehint(Bar)): ...`` and return the created class."""
    class Foo(with_typehint(Bar)):
        pass

    return Foo

def test_with_typehint_returns_object_at_runtime():
    assert with_typehint(Bar) is object


def test_with_typehint_can_be_used_as_a_base_class(hinted_class):
    assert isinstance(hinted_class, type)
    assert hinted_class.__bases__ == (object,)

def test_with_typehint_class_creation_follows_documented_pattern():
    class Foo(with_typehint(Bar)):
        pass

    assert Foo.__mro__ == (Foo, object)

def test_with_typehint_does_not_copy_annotations_at_runtime():
    class Foo(with_typehint(Bar)):
        pass

    assert 'value' not in Foo.__dict__.get('__annotations__', {})

def test_with_typehint_preserves_own_annotations_of_derived_class():
    class Foo(with_typehint(Bar)):
        count: int = 7

    assert Foo.__dict__['__annotations__'] == {'count': int}
    assert Foo.count == 7

def test_with_typehint_does_not_inherit_members_of_hint_class_at_runtime():
    class Foo(with_typehint(Bar)):
        pass

    foo = Foo()

    assert not hasattr(foo, 'bar_method')
    assert not hasattr(foo, 'value')

def test_with_typehint_instance_is_not_an_instance_of_hint_class():
    class Foo(with_typehint(Bar)):
        pass

    assert isinstance(Foo(), Bar) is False

def test_with_typehint_instance_behaves_like_a_plain_object():
    class Foo(with_typehint(Bar)):
        pass

    first = Foo()
    second = Foo()

    assert isinstance(first, object)
    assert first.__class__ is Foo

    # ``object`` equality is identity-based: an instance equals itself ...
    assert first == first
    # ... but two distinct instances are not equal.
    assert first != second


def test_with_typehint_derived_class_can_define_its_own_members():
    class Foo(with_typehint(Bar)):
        def __init__(self, value):
            self.value = value

        def double(self):
            return self.value * 2

    foo = Foo(21)

    assert foo.value == 21
    assert foo.double() == 42

def test_with_typehint_derived_class_can_be_subclassed_further():
    class Base(with_typehint(Bar)):
        def greet(self):
            return 'hi'

    class Child(Base):
        pass

    assert Child().greet() == 'hi'
    assert issubclass(Child, Base)

@pytest.mark.parametrize('baseclass', [Bar, dict, list, object, int, FrozenDict, LRUCache])
def test_with_typehint_accepts_any_class_and_returns_object(baseclass):
    assert with_typehint(baseclass) is object

@pytest.mark.parametrize('hint', [List[int], Optional[int], Union[int, str], Type[int]])
def test_with_typehint_accepts_typing_constructs(hint):
    assert with_typehint(hint) is object

    class Foo(with_typehint(hint)):
        pass

    assert Foo.__bases__ == (object,)

@pytest.mark.parametrize('value', [None, 42, 'Bar', 3.5, [Bar], {'a': 1}, lambda: None])
def test_with_typehint_ignores_non_class_arguments(value):
    assert with_typehint(value) is object

def test_with_typehint_requires_exactly_one_argument():
    with pytest.raises(TypeError):
        with_typehint()

def test_with_typehint_rejects_extra_arguments():
    with pytest.raises(TypeError):
        with_typehint(Bar, dict)

def test_with_typehint_accepts_keyword_argument():
    assert with_typehint(baseclass=Bar) is object

def test_with_typehint_returns_same_object_for_repeated_calls():
    assert with_typehint(Bar) is with_typehint(dict) is object

def test_with_typehint_does_not_inspect_the_given_class():
    class ExplodingMeta(type):
        def __getattribute__(cls, name):
            raise AssertionError('with_typehint must not inspect the given class')

    exploding = ExplodingMeta('Exploding', (), {})

    assert with_typehint(exploding) is object

    class Foo(with_typehint(exploding)):
        pass

    assert Foo.__mro__ == (Foo, object)

def test_with_typehint_does_not_preserve_mapping_behaviour_of_hint_class():
    class Frozen(with_typehint(FrozenDict)):
        pass

    instance = Frozen()

    assert isinstance(instance, FrozenDict) is False
    assert isinstance(instance, dict) is False
