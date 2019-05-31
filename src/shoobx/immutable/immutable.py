###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""Immutable Objects."""

import collections
import functools
import zope.interface
from contextlib import contextmanager

from shoobx.immutable import interfaces


def update(im, *args, **kw):
    """Update an immutable object.

    This is a helper method for ``IImmutable.__im_update__(*args, **kw)``.
    """
    return im.__im_update__(*args, **kw)


def failOnNonTransient(func):
    """Only allow function execution when immutable is transient."""

    @functools.wraps(func)
    def wrapper(inst, *args, **kwargs):
        # make the call fail if the object is not transient
        if inst.__im_state__ != interfaces.IM_STATE_TRANSIENT:
            raise AttributeError('Cannot update locked immutable object.')
        return func(inst, *args, **kwargs)

    return wrapper


def applyStateOnInit(func):
    """Handle immutable internal arguments to the constructor."""

    @functools.wraps(func)
    def wrapper(self, *args, im_finalize=True, im_mode=None, **kw):
        func(self, *args, **kw)
        if im_mode is not None:
            self.__im_mode__ = im_mode
        if im_finalize:
            self.__im_finalize__()

    return wrapper


@zope.interface.implementer(interfaces.IImmutable)
class ImmutableBase:
    """Immutable Base

    Core functionality for all immutable objects.

    While the class can be used directly, it is meant to be a base class only.
    """

    __im_mode__ = interfaces.IM_MODE_DEFAULT
    __im_state__ = interfaces.IM_STATE_TRANSIENT

    @applyStateOnInit
    def __init__(self):
        # this is here to make the ImmutableMeta wrapper work
        # with classes having no __init__
        pass

    def __im_conform__(self, object):
        # The returned object will be a slave of `self`
        # `self.__im_state__` must be propagated to all slaves
        mode = interfaces.IM_MODE_SLAVE

        # All core immutable types are allowed to be set at all times.
        if isinstance(object, interfaces.IMMUTABLE_TYPES):
            return object

        # Any immutable object can be converted. It simply returns itself if
        # transient, otherwise it creates a transient clone of itself.
        if interfaces.IImmutable.providedBy(object):
            if object.__im_state__ != interfaces.IM_STATE_TRANSIENT:
                object = object.__im_clone__()
            object.__im_mode__ = mode
            return object

        # All dict types are automatically converted to their immutable
        # equivalent.
        if isinstance(object, interfaces.DICT_TYPES):
            return ImmutableDict(object, im_finalize=False, im_mode=mode)

        # All list types are automatically converted to their immutable
        # equivalent.
        if isinstance(object, interfaces.LIST_TYPES):
             return ImmutableList(object, im_finalize=False, im_mode=mode)

        # All set types are automatically converted to their immutable
        # equivalent.
        if isinstance(object, interfaces.SET_TYPES):
            return ImmutableSet(object, im_finalize=False, im_mode=mode)

        # Get the object's equivalent immutable.
        if hasattr(object, '__im_get__'):
            # assert that the new value is locked?
            newobj = object.__im_get__(mode=mode)
            assert interfaces.IImmutable.providedBy(newobj)
            assert newobj.__im_state__ == interfaces.IM_STATE_TRANSIENT
            assert newobj.__im_mode__ == mode
            return newobj

        raise ValueError('Unable to conform object to immutable.', object)

    def __im_clone__(self):
        # Create an exact clone of the current object.
        clone = self.__class__.__new__(self.__class__)
        for key, value in self.__dict__.items():
            if interfaces.IImmutable.providedBy(value):
                value = value.__im_clone__()
            clone.__dict__[key] = value
        # Make sure the clone is transient.
        clone.__im_state__ = interfaces.IM_STATE_TRANSIENT
        # Return the clone.
        return clone

    def __im_finalize__(self):
        # Do not allow finalization on anything but a transient state:
        if self.__im_state__ != interfaces.IM_STATE_TRANSIENT:
            raise RuntimeError(
                f'Cannot finalize an immutable in state: {self.__im_state__}')
        self.__im_set_state__(interfaces.IM_STATE_LOCKED)

    def __im_set_state__(self, state):
        self.__im_state__ = state
        # Propagate state to all IImmutable sub objects.
        for subobj in self.__dict__.values():
            if interfaces.IImmutable.providedBy(subobj):
                subobj.__im_set_state__(state)

    def __im_before_update__(self, clone):
        pass

    def __im_after_update__(self, clone):
        pass

    @contextmanager
    def __im_update__(self, *args, **kw):
        # Only a master immutable can be updated directly.
        if self.__im_mode__ != interfaces.IM_MODE_MASTER:
            raise AttributeError(
                'update() is only available for master immutables.')

        # If we already have a transient immutable, then just use it.
        if self.__im_state__ == interfaces.IM_STATE_TRANSIENT:
            yield self
            return

        # Create a transient clone of itself.
        clone = self.__im_clone__()
        assert clone.__im_state__ == interfaces.IM_STATE_TRANSIENT

        self.__im_before_update__(clone, *args, **kw)
        try:
            yield clone
        except:
            raise
        clone.__im_finalize__()
        self.__im_after_update__(clone, *args, **kw)

    def __im_is_internal_attr__(self, name):
        return name.startswith('__') and name.endswith('__')

    def __setattr__(self, name, value):
        # Internal attributes can always be updated irregardless of state.
        if self.__im_is_internal_attr__(name):
            super().__setattr__(name, value)
            return

        if interfaces.IImmutable.providedBy(value):
            # do not allow setting a slave mode object
            assert value.__im_mode__ == interfaces.IM_MODE_MASTER

        # Only allow object update while in a transient state.
        if self.__im_state__ != interfaces.IM_STATE_TRANSIENT:
            raise AttributeError('Cannot update locked immutable object.')

        im_value = self.__im_conform__(value)
        super().__setattr__(name, im_value)


class ImmutableMeta(type):

    def __new__(cls, name, bases, dct):
        if '__init__' in dct:
            dct['__init__'] = applyStateOnInit(dct['__init__'])
        return super().__new__(cls, name, bases, dct)


@zope.interface.implementer(interfaces.IImmutableObject)
class Immutable(ImmutableBase, metaclass=ImmutableMeta):
    pass


@zope.interface.implementer(interfaces.IImmutable)
class ImmutableDict(ImmutableBase, collections.UserDict):

    @applyStateOnInit
    def __init__(self, *args, **kw):
        # need to avoid calling ImmutableBase.__init__ here
        collections.UserDict.__init__(self)
        # make sure all values go through OUR `__setitem__`
        if args:
            for key, value in args[0].items():
                self[key] = value
        for key, value in kw.items():
            self[key] = value

    def __im_clone__(self):
        # Create an exact clone of the current object.
        newdata = {
            key: self.__im_conform__(value)
            for key, value in self.data.items()
        }
        dct = self.__class__(im_finalize=False)
        dct.data.update(newdata)
        return dct

    def __im_set_state__(self, state):
        super().__im_set_state__(state)
        # Propagate state to all dict values.
        for subobj in self.values():
            if interfaces.IImmutable.providedBy(subobj):
                subobj.__im_set_state__(state)

    def __im_is_internal_attr__(self, name):
        if name == 'data':
            return True
        return super().__im_is_internal_attr__(name)

    @failOnNonTransient
    def __setitem__(self, key, value):
        if interfaces.IImmutable.providedBy(value):
            # do not allow setting a slave mode object
            assert value.__im_mode__ == interfaces.IM_MODE_MASTER
        im_value = self.__im_conform__(value)
        super().__setitem__(key, im_value)

    @failOnNonTransient
    def __delitem__(self, key):
        super().__delitem__(key)

    def copy(self):
        # Only allow copy in locked state, otherwise a shallow clone cannot be
        # produced.
        assert self.__im_state__ == interfaces.IM_STATE_LOCKED
        # Returns a shallow copy, which allows a simple transfer of data.
        copy = self.__class__()
        copy.data = self.data.copy()
        return copy

    @failOnNonTransient
    def clear(self):
        return self.data.clear()

    @failOnNonTransient
    def update(self, dct):
        for key, value in dct.items():
            # Need to loop through the items instead of self.data.update(dct)
            # because we need to __im_conform__ the items.
            self[key] = value

    @failOnNonTransient
    def setdefault(self, key, default=None):
        im_default = self.__im_conform__(default)
        return super().setdefault(key, im_default)

    @failOnNonTransient
    def pop(self, key, *args):
        return super().pop(key, *args)

    @failOnNonTransient
    def popitem(self):
        return super().popitem()

    @classmethod
    def fromkeys(cls, iterable, value=None):
        dct = cls(im_finalize=False)
        for key in iterable:
            dct[key] = value
        dct.__im_finalize__()
        return dct

    def __getstate__(self):
        return self.data

    def __setstate__(self, state):
        self.data = state


@zope.interface.implementer(interfaces.IImmutable)
class ImmutableSet(ImmutableBase, collections.abc.MutableSet):

    @applyStateOnInit
    def __init__(self, *args, **kw):
        # need to avoid calling ImmutableBase.__init__ here
        collections.abc.MutableSet.__init__(self)
        self.__data__ = set()
        if args:
            # make sure all values go through OUR `add`
            for value in args[0]:
                self.add(value)

    def __im_set_state__(self, state):
        super().__im_set_state__(state)
        # Propagate state to all values.
        for subobj in self.__data__:
            if interfaces.IImmutable.providedBy(subobj):
                subobj.__im_set_state__(state)

    def __im_clone__(self):
        # Create an exact clone of the current object.
        newdata = set([self.__im_conform__(value) for value in self.__data__])
        rset = self.__class__(im_finalize=False)
        rset.__data__.update(newdata)
        return rset

    @failOnNonTransient
    def add(self, value):
        if interfaces.IImmutable.providedBy(value):
            # do not allow setting a slave mode object
            assert value.__im_mode__ == interfaces.IM_MODE_MASTER
        im_value = self.__im_conform__(value)
        self.__data__.add(im_value)

    @failOnNonTransient
    def discard(self, value):
        self.__data__.discard(value)

    def __contains__(self, key):
        return key in self.__data__

    def __iter__(self):
        return iter(self.__data__)

    def __len__(self):
        return len(self.__data__)

    def __hash__(self):
        return frozenset(self.__data__).__hash__()

    def __repr__(self):
        return repr(self.__data__)


@zope.interface.implementer(interfaces.IImmutable)
class ImmutableList(ImmutableBase, collections.UserList):

    @applyStateOnInit
    def __init__(self, *args, **kw):
        # need to avoid calling ImmutableBase.__init__ here
        collections.UserList.__init__(self)
        if args:
            # make sure all values go through OUR `append`
            for value in args[0]:
                self.append(value)

    def __im_is_internal_attr__(self, name):
        if name == 'data':
            return True
        return super().__im_is_internal_attr__(name)

    def __im_clone__(self):
        # Create an exact clone of the current object.
        newdata = [self.__im_conform__(value) for value in self.data]
        clone = self.__class__(im_finalize=False)
        clone.data.extend(newdata)
        return clone

    def __im_set_state__(self, state):
        super().__im_set_state__(state)
        # Propagate state to all subjects.
        for subobj in self:
            if interfaces.IImmutable.providedBy(subobj):
                subobj.__im_set_state__(state)

    @failOnNonTransient
    def __setitem__(self, i, value):
        if interfaces.IImmutable.providedBy(value):
            # do not allow setting a slave mode object
            assert value.__im_mode__ == interfaces.IM_MODE_MASTER
        value = self.__im_conform__(value)
        super().__setitem__(i, value)

    @failOnNonTransient
    def __delitem__(self, i):
        super().__delitem__(i)

    def copy(self):
        # Only allow copy in locked state, otherwise a shallow clone cannot be
        # produced.
        assert self.__im_state__ == interfaces.IM_STATE_LOCKED
        # Returns a shallow copy, which allows a simple transfer of data.
        copy = self.__class__()
        copy.data = self.data.copy()
        return copy

    @failOnNonTransient
    def append(self, item):
        if interfaces.IImmutable.providedBy(item):
            # do not allow setting a slave mode object
            assert item.__im_mode__ == interfaces.IM_MODE_MASTER
        item = self.__im_conform__(item)
        super().append(item)

    @failOnNonTransient
    def extend(self, other):
        for v in other:
            self.append(v)

    def __add__(self, other):
        return self.__class__(self.data + list(other))

    @failOnNonTransient
    def __iadd__(self, other):
        for v in other:
            self.append(v)
        return self

    @failOnNonTransient
    def __imul__(self, n):
        for item in self:
            if interfaces.IImmutable.providedBy(item):
                # Do not allow duplicating a slave mode object.
                # Hopefully no need to check the whole tree
                # it should be impossible to put an IImmutable object
                # somewhere on a lower level without having it in an other
                # IImmutable.
                assert item.__im_mode__ == interfaces.IM_MODE_MASTER
        self.data *= n
        return self

    @failOnNonTransient
    def insert(self, i, item):
        if interfaces.IImmutable.providedBy(item):
            # do not allow setting a slave mode object
            assert item.__im_mode__ == interfaces.IM_MODE_MASTER
        item = self.__im_conform__(item)
        super().insert(i, item)

    @failOnNonTransient
    def pop(self, i=-1):
        return super().pop(i)

    @failOnNonTransient
    def remove(self, item):
        super().remove(item)

    @failOnNonTransient
    def clear(self):
        super().clear()

    @failOnNonTransient
    def reverse(self):
        super().reverse()

    @failOnNonTransient
    def sort(self, *args, **kwds):
        super().sort()
