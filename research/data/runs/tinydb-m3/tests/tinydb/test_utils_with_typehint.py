import pytest
from tinydb.utils import with_typehint

def test_with_typehint_returns_object_at_runtime():
    """At runtime, with_typehint should always return ``object``."""
    class Bar:
        pass

    assert with_typehint(Bar) is object


def test_with_typehint_returns_a_type():
    """The return value of with_typehint must be a class (type)."""
    class Bar:
        pass

    result = with_typehint(Bar)
    assert isinstance(result, type)


def test_with_typehint_usable_as_base_class():
    """The return value of with_typehint must be usable as a base class."""
    class Bar:
        pass

    # Defining this class must not raise; this exercises the documented usage.
    class Foo(with_typehint(Bar)):
        pass

    assert isinstance(Foo, type)


def test_class_with_typehint_inherits_from_object():
    """A class defined using with_typehint must inherit from ``object``."""
    class Bar:
        pass

    class Foo(with_typehint(Bar)):
        pass

    assert issubclass(Foo, object)


def test_class_with_typehint_can_be_instantiated():
    """A class defined using with_typehint should be instantiable like a normal class."""
    class Bar:
        pass

    class Foo(with_typehint(Bar)):
        def __init__(self, value):
            self.value = value

    instance = Foo(42)
    assert instance.value == 42
    assert isinstance(instance, object)


def test_with_typehint_with_builtin_class():
    """with_typehint should work when the hint source is a built-in class."""
    class Foo(with_typehint(dict)):
        pass

    assert issubclass(Foo, object)
    assert isinstance(Foo(), object)


def test_with_typehint_with_custom_user_class():
    """with_typehint should work when the hint source is a user-defined class."""
    class MyBase:
        attr = 1

    class Foo(with_typehint(MyBase)):
        pass

    foo = Foo()
    assert isinstance(foo, object)
    # At runtime the type hint is not enforced, so the attribute is absent.
    assert not hasattr(foo, 'attr')


def test_with_typehint_independent_of_input():
    """with_typehint should return ``object`` regardless of which class is passed."""
    class A:
        pass

    class B:
        pass

    # The return value is independent of the argument supplied at runtime.
    assert with_typehint(A) is with_typehint(B)
    assert with_typehint(A) is object
    assert with_typehint(B) is object


def test_with_typehint_object_is_in_mro():
    """``object`` must appear in the MRO of any class built with with_typehint."""
    class Bar:
        pass

    class Foo(with_typehint(Bar)):
        pass

    assert object in Foo.__mro__


def test_with_typehint_input_class_not_in_mro():
    """The hint source class must NOT be in the MRO at runtime."""
    class Bar:
        def bar_method(self):
            return "from Bar"

    class Foo(with_typehint(Bar)):
        pass

    # Bar must not be a real base class at runtime.
    assert not issubclass(Foo, Bar)
    assert Bar not in Foo.__mro__
    assert not hasattr(Foo, 'bar_method')


def test_with_typehint_with_object_as_input():
    """Passing ``object`` itself as the hint source must also yield ``object``."""
    class Foo(with_typehint(object)):
        pass

    assert issubclass(Foo, object)
    assert Foo.__bases__ == (object,)


def test_with_typehint_subclassable_class_remains_subclassable():
    """A class defined with with_typehint can itself be subclassed normally."""
    class Bar:
        pass

    class Foo(with_typehint(Bar)):
        pass

    class Baz(Foo):
        pass

    assert issubclass(Baz, Foo)
    assert issubclass(Baz, object)
