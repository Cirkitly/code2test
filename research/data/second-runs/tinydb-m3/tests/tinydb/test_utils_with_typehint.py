import pytest
from tinydb.utils import with_typehint

def test_with_typehint_returns_object_for_builtin_type():
    """At runtime, with_typehint always returns the object class for builtin types."""
    # The function ignores its argument at runtime (TYPE_CHECKING is False).
    # It returns ``object`` so that the metaclass machinery can still build
    # a usable class.
    assert with_typehint(str) is object


def test_with_typehint_returns_object_for_custom_class():
    """with_typehint returns object when given a user-defined class."""
    class Bar:
        """A stand-in user-defined class used purely as an argument."""
        pass

    # The runtime branch ignores ``Bar`` and substitutes ``object``.
    assert with_typehint(Bar) is object


def test_class_created_with_with_typehint_can_be_defined():
    """The documented ``class Foo(with_typehint(Bar))`` pattern is valid Python."""
    class Bar:
        pass

    # This must not raise; the result must be a valid class.
    class Foo(with_typehint(Bar)):
        pass

    assert isinstance(Foo, type)


def test_class_created_with_with_typehint_inherits_from_object():
    """A class built with with_typehint inherits from object, not from baseclass."""
    class Bar:
        pass

    class Foo(with_typehint(Bar)):
        pass

    # The runtime branch substitutes ``object`` for the real baseclass,
    # so ``Foo``'s sole base must be ``object``.
    assert Foo.__bases__ == (object,)
    assert issubclass(Foo, object)
    # And critically, ``Foo`` must NOT be a subclass of ``Bar`` at runtime.
    assert not issubclass(Foo, Bar)


def test_class_using_with_typehint_supports_attributes_and_methods():
    """A class built with with_typehint can hold attributes and methods normally."""
    class Bar:
        def bar_method(self):
            return "bar"

    class Foo(with_typehint(Bar)):
        def __init__(self, value):
            self.value = value

        def get_value(self):
            return self.value

    instance = Foo(42)
    assert instance.value == 42
    assert instance.get_value() == 42


def test_class_using_with_typehint_does_not_inherit_methods_from_base_at_runtime():
    """Methods on the baseclass argument are NOT inherited at runtime."""
    class Bar:
        def bar_method(self):
            return "bar"

    class Foo(with_typehint(Bar)):
        pass

    instance = Foo()
    # ``object`` has no ``bar_method``; the runtime contract is that
    # ``Bar`` is *not* a real base, so the method must be missing.
    with pytest.raises(AttributeError):
        instance.bar_method()


def test_with_typehint_returns_a_class_object():
    """The value returned by with_typehint must be a valid class usable as a base."""
    class Bar:
        pass

    base = with_typehint(Bar)
    # The return value must be a class object itself so it can be used
    # inside the ``bases`` tuple of a class statement.
    assert isinstance(base, type)


def test_with_typehint_results_are_consistent_across_inputs():
    """with_typehint returns the same singleton object regardless of input class."""
    class Bar:
        pass

    # All these calls must evaluate to the *same* ``object`` instance at
    # runtime, because the argument is only consulted by the type checker.
    assert with_typehint(Bar) is with_typehint(str)
    assert with_typehint(int) is with_typehint(dict)
    assert with_typehint(object) is with_typehint(type)


def test_with_typehint_works_with_dataclass_like_class():
    """Edge case: with_typehint works when used with a class that defines __init_subclass__ hooks (so long as the base is itself a regular class)."""
    class Bar:
        marker = "bar-marker"

    class Foo(with_typehint(Bar)):
        marker = "foo-marker"

    # The runtime base is ``object``, so the class attribute on ``Foo`` wins.
    assert Foo.marker == "foo-marker"
    # The marker is defined directly in Foo's own __dict__, confirming the
    # attribute comes from Foo itself (not from Bar at runtime).
    assert Foo.__dict__["marker"] == "foo-marker"

