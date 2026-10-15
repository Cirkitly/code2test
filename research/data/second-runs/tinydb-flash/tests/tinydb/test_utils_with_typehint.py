import pytest
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import tinydb.utils
from tinydb.utils import with_typehint, FrozenDict, LRUCache

import pytest
from tinydb.utils import with_typehint


def test_returns_object_as_runtime_base_class():
    """At runtime ``with_typehint`` must evaluate to ``object`` itself."""
    class Bar:
        """The class whose type hints should be borrowed."""

    result = with_typehint(Bar)

    assert result is object
    # The returned value must be usable as a base class in a class statement
    assert isinstance(result, type)
    assert issubclass(result, object)

import pytest
from tinydb.utils import with_typehint


def test_generated_class_is_not_subclass_of_annotated_class():
    """The annotated class is only a hint: no real runtime inheritance happens."""
    class Bar:
        def method(self):
            return 'bar'

    class Foo(with_typehint(Bar)):
        pass

    assert issubclass(Foo, object)
    assert not issubclass(Foo, Bar)
    assert Bar not in Foo.__mro__
    assert Foo.__mro__ == (Foo, object)

import pytest
from tinydb.utils import with_typehint


def test_instance_creation_ignores_annotated_class_constructor():
    """Instances of the generated class are plain objects with a no-arg constructor."""
    class Bar:
        def __init__(self, required_argument):
            self.required_argument = required_argument

    class Foo(with_typehint(Bar)):
        pass

    # No TypeError even though Bar.__init__ requires an argument
    foo = Foo()

    assert isinstance(foo, Foo)
    assert not hasattr(foo, 'required_argument')

import pytest
from tinydb.utils import with_typehint


def test_instance_does_not_inherit_annotated_class_attributes():
    """Members of the annotated class are unavailable on the generated class."""
    class Bar:
        marker = 'bar'

        def method(self):
            return 'bar-method'

    class Foo(with_typehint(Bar)):
        pass

    foo = Foo()

    with pytest.raises(AttributeError):
        foo.marker

    with pytest.raises(AttributeError):
        foo.method()

import pytest
from tinydb.utils import with_typehint


def test_with_typehint_does_not_modify_the_annotated_class():
    """The annotated class keeps its own bases, attributes and MRO."""
    class Base:
        pass

    class Bar(Base):
        marker = 'bar'

        def __init__(self, value):
            self.value = value

    original_bases = Bar.__bases__
    original_mro = Bar.__mro__

    class Foo(with_typehint(Bar)):
        pass

    assert Bar.__bases__ is original_bases
    assert Bar.__mro__ == original_mro
    assert Base in Bar.__mro__
    assert Bar('x').value == 'x'
    assert Bar('x').marker == 'bar'

import pytest
from tinydb.utils import with_typehint, FrozenDict, LRUCache


@pytest.mark.parametrize('baseclass', [FrozenDict, LRUCache, dict, list])
def test_accepts_project_classes_as_annotation_target(baseclass):
    """Any class (including TinyDB's own) can be passed as the annotation target."""
    class Foo(with_typehint(baseclass)):
        pass

    assert with_typehint(baseclass) is object
    assert issubclass(Foo, object)
    assert not issubclass(Foo, baseclass)

import pytest
from tinydb.utils import with_typehint


@pytest.mark.parametrize('not_a_class', [None, 42, 'Bar', object(), lambda: None, [int]])
def test_with_typehint_does_not_validate_its_argument_at_runtime(not_a_class):
    """The runtime branch performs no type checking of its argument."""
    assert with_typehint(not_a_class) is object

import pytest
from abc import ABC, abstractmethod

from tinydb.utils import with_typehint


def test_with_typehint_of_abstract_class_returns_object():
    """An abstract annotation target does not make the generated class abstract."""
    class AbstractBase(ABC):
        @abstractmethod
        def do(self):
            raise NotImplementedError

    class Foo(with_typehint(AbstractBase)):
        pass

    # At runtime the helper simply returns `object`, ignoring the given base class
    assert with_typehint(AbstractBase) is object

    # Instantiable because the runtime base is plain `object`
    instance = Foo()
    assert isinstance(instance, Foo)

    # ... and no members of the abstract base leaked into the new class
    assert not hasattr(instance, 'do')

import pytest
from tinydb.utils import with_typehint


def test_with_typehint_result_can_be_shared_by_multiple_classes():
    """The returned base can be reused; each subclass gets its own plain MRO."""
    class Bar:
        pass

    base = with_typehint(Bar)

    class First(base):
        pass

    class Second(base):
        pass

    assert base is object
    assert First.__mro__ == (First, object)
    assert Second.__mro__ == (Second, object)
    assert not issubclass(First, Second)
    assert not issubclass(Second, Bar)

import pytest
from tinydb.utils import with_typehint


def test_generated_class_supports_basic_object_protocol():
    """The generated class behaves like a regular `object` subclass."""
    class Bar:
        def method(self):
            return 'bar'

    class Foo(with_typehint(Bar)):
        pass

    foo = Foo()

    assert isinstance(foo, Foo)
    assert isinstance(foo, object)
    assert foo == foo
    assert isinstance(hash(foo), int)
    assert isinstance(repr(foo), str)
    assert isinstance(str(foo), str)

import pytest
from tinydb.utils import with_typehint


def test_nested_with_typehint_returns_object():
    """Applying ``with_typehint`` to an already processed base still yields ``object``."""
    class Bar:
        pass

    result = with_typehint(with_typehint(Bar))

    assert result is object

    class Foo(result):
        pass

    assert Foo.__mro__ == (Foo, object)

import pytest
from typing import TYPE_CHECKING

import tinydb.utils
from tinydb.utils import with_typehint


def test_returns_baseclass_when_type_checking_is_enabled(monkeypatch):
    """Under type checking, ``with_typehint`` returns the given base class."""
    assert TYPE_CHECKING is False

    class Bar:
        pass

    monkeypatch.setattr(tinydb.utils, 'TYPE_CHECKING', True, raising=True)

    assert with_typehint(Bar) is Bar

    class Foo(with_typehint(Bar)):
        pass

    assert issubclass(Foo, Bar)
