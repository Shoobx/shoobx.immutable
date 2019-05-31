###############################################################################
#
# Copyright 2013-2018 by Shoobx, Inc.
#
###############################################################################
"""Revisioned Immutable and Container."""

import collections.abc
import datetime
import zope.interface
from contextlib import contextmanager

from shoobx.immutable import immutable, interfaces


@zope.interface.implementer(interfaces.IRevisionedImmutable)
class RevisionedImmutableBase(immutable.ImmutableBase):

    __im_version__ = 0
    __im_start_on__ = None
    __im_end_on__ = None
    __im_creator__ = None
    __im_comment__ = None
    __im_manager__ = None

    def __im_before_update__(self, clone, creator=None, comment=None):
        # Assign the update information to the clone:
        clone.__im_creator__ = creator
        clone.__im_comment__ = comment
        clone.__im_version__ = self.__im_version__ + 1

    def __im_after_update__(self, clone, creator=None, comment=None):
        if self.__im_manager__ is not None:
            self.__im_manager__.addRevision(clone, old=self)


class RevisionedImmutable(
        RevisionedImmutableBase, metaclass=immutable.ImmutableMeta):
    pass


@zope.interface.implementer(interfaces.IRevisionedImmutableManager)
class SimpleRevisionedImmutableManager:

    # testing hook, make sure this returns a steady increasing timestamp
    # on each call, a static datetime does NOT cut it
    now = datetime.datetime.now

    def __init__(self):
        self.__data__ = []

    def getCurrentRevision(self, obj=None):
        if not self.__data__:
            return None
        if self.__data__[-1].__im_end_on__ is not None:
            return None
        return self.__data__[-1]

    def getRevisionHistory(self, obj=None):
        return self.__data__

    def addRevision(self, new, old=None):
        now = self.now()
        if old is not None:
            old.__im_end_on__ = now
            old.__im_state__ = interfaces.IM_STATE_RETIRED

        new.__im_start_on__ = now
        new.__im_manager__ = self
        assert new.__im_state__ == interfaces.IM_STATE_LOCKED
        self.__data__.append(new)

    def rollbackToRevision(self, revision, activate=True):
        idx = self.__data__.index(revision)
        self.__data__ = self.__data__[0:idx-1]
        if activate:
            revision.__im_end_on__ = None
            revision.__im_state__ = interfaces.IM_STATE_LOCKED


class RevisionedMapping(collections.abc.MutableMapping):

    def __init__(self):
        self.__data__ = {}

    def getRevisionManager(self, key):
        if key not in self.__data__:
            raise KeyError(key)
        return self.__data__[key]

    def __len__(self):
        return len(self.__data__)

    def __iter__(self):
        return iter(self.__data__)

    def __getitem__(self, key):
        revisions = self.getRevisionManager(key)
        return revisions.getCurrentRevision()

    def __setitem__(self, key, value):
        self.__data__[key] = SimpleRevisionedImmutableManager()
        self.__data__[key].addRevision(value)

    def __delitem__(self, key):
        del self.__data__[key]
