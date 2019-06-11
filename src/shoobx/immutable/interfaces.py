###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""Immutable Interfaces."""

import datetime
import decimal

import zope.interface
import zope.lifecycleevent
import zope.schema

IM_MODE_MASTER = 'master'
IM_MODE_SLAVE = 'slave'
IM_MODE_DEFAULT = IM_MODE_MASTER
IM_MODES = (IM_MODE_MASTER, IM_MODE_SLAVE)

IM_STATE_LOCKED = 'locked'
IM_STATE_TRANSIENT = 'transient'
IM_STATES = (IM_STATE_LOCKED, IM_STATE_TRANSIENT)

IM_STATE_RETIRED = 'retired'
IM_STATES_REVISIONED = (IM_STATE_LOCKED, IM_STATE_TRANSIENT, IM_STATE_RETIRED)

IMMUTABLE_TYPES = (
    bool, int, float, complex, decimal.Decimal, tuple, str, bytes, type(None),
    datetime.date, datetime.time, datetime.datetime, datetime.timedelta,
    datetime.tzinfo,
)

LIST_TYPES = (
    list,
)

DICT_TYPES = (
    dict,
)

SET_TYPES = (
    set,
)


class IImmutable(zope.interface.Interface):
    """Immutable Object

    In an immutable object no data can be modified. To modify state, a copy
    of the object must be created into which the changes are applied.

    When trying to modify an attribute of a locked immutable, an
    `AttributeError` is raised with the message saying that the attribute
    cannot be set. The only exceptions are internal attributes which are
    determined using the `__im_is_internal_attr__(name) -> bool` method.

    Immutables are updated using the `__im_update__()` context manager in the
    following way::

      im = Immutable(attr=value)
      with im.__im_update__() as im2:
          im2.attr = value2

    In the example above, `im` is not modified and all changes are applied to
    `im2`.

    The algorithm works as follows:

    1. The `__im_update__()` method is used to create a context manager.

    2. Upon entering the context manager, a clone of the original immutable is
       created and returned as context.

    3. The clone is in the `transient` state, allowing all data to be
       modified. Note that modifications can be made at any depth in the
       object.

    4. Upon exiting the context manager, the clone is put in the `locked`
       state.

    Internally, updating deeply nested objects is managed by assigning a mode
    to the immutable. The `master` mode describes an immutable that can be
    updated while a `slave` (sub-object) is updated as part of its master. The
    following rules apply:

    1. All immutable sub-objects must be `slave` immutables.

    2. A `master` immutable cannot be assigned or added to another immutable,
       whether that's a `master` or `slave`.

    3. Only `master` immutables can call `__im_update__()`.

    4. Any immutable object can only have sub-objects that are also immutable
       or can be made immutable upon assignment.[1]

    ..[1] During initialization all class attributes are checked to be
          immutable or are converted to immutables. On assignment, any mutable
          object is converted into an immutable object. If convertsion to an
          immutable object fails, a `ValueError` error is raised.

    Conversion of mutable to immutable objects:

    1. All immutable objects are ignored. These object include all Python core
       immutables and any object providing this `IImmutable` interface.

    2. A conversion from lists, dicts and sets is provided.

    3. A mutable object can implement the `__im_get__()` method to provide an
       immutable version of itself.  Note: `__im_get__()` must NOT return the
       same object instance!
    """

    __im_mode__ = zope.schema.Choice(
        title=u'Immutable Mode',
        values=IM_MODES,
        default=IM_MODE_DEFAULT
    )

    __im_state__ = zope.schema.Choice(
        title=u'Immutable State',
        values=IM_STATES,
        default=IM_STATE_TRANSIENT
    )

    def __im_conform__(object):
        """Get an immutable version of the object.

        This method converts the given object into its immutable self.

        The return value will either be a core immutable object or an object
        implementing the `IImmutable` interface. If the latter is returned,
        it must be in `IM_MODE_SLAVE` mode and in the `IM_STATE_TRANSIENT`
        state.

        When having an `IImmutable` object, we must ensure that the result is
        in the transient state. Thus, if the immutable is already in the
        transient state, just return it, otherwise create a transient clone of
        it.

        This method is intended for internal use only and should only be
        called for sub-objects while adding them to the immutable. The
        resulting immutable must also be in the `IM_STATE_TRANSIENT`
        state.

        Raises a `ValueError` exception if the object cannot be converted.
        """

    def __im_clone__():
        """Return a clone of itself.

        Important: This method produces a deep clone of itself in `transient`
        mode.
        """

    def __im_set_state__(state):
        """Set state on the object and all sub objects

        Sub-objects are objects in attributes, dict values, list items, etc.
        """

    def __im_finalize__():
        """Finalize the object.

        The immutable and all its sub-objects are being `locked` to disallow
        any further write access.
        """

    def __im_before_update__(clone):
        """Hook called before `__im_update__()`

        It is called after a clone in transient state has been created and self
        is retired.
        """

    def __im_after_update__(clone):
        """Hook called at the end of `__im_update__()`.

        This method is called while exiting the context manager but before
        finalizing the clone.
        Thus, the clone object is still in transient state.
        """

    def __im_update__():
        """Returns a context manager allowing the context to be modified.

        If the immutable is initially in the `locked` state, then a clone in
        the `transient` state is created and provided as context.

        If the immutable is already in the `transient` state, then the object
        itself is returned.
        """

    def __setattr__(name, value):
        """Set the new attribute value for the given name.

        If the value is not an immutable, an `AttributeError` will be raised.
        """


class IImmutableObject(IImmutable):
    """Immutable Type.

    Specific interface to mark general immutable classes.

    All immutable objcets will support two constructor arguments implicitly:

    (1) `im_finalize = True`: When true, the object will be created in the
        locked state. That is particularly useful when all data is set inside
        the constructor.

    (2) `im_mode = None`: If a mode is provided, the created immutable will be
        set to this mode.
    """


class IRevisionedImmutableManager(zope.interface.Interface):
    """Revisioned immutable contianer.

    This interface is agnostic on how the underlying object is identified from
    the revision. A sensible implementation is to have a deignated attribute
    for the name of the object.
    """

    def getRevisionHistory(obj):
        """Returns list of all revisions of the object in chronological order.
        """

    def getCurrentRevision(obj):
        """Get the currently active revision of the object.

        If no revision or active revision is found for the object, `None` is
        returned.
        """

    def addRevision(new, old=None):
        """Add a new revision.

        This method should be implemented to allow a simple append operation
        to the revision history.

        It must assign the `__im_start_on__` attribute of the `new` revision
        to the current date/time. Also, the `__im_manager__` attribute will be
        set to this `IRevisionedImmutableManager` instance. It is assumed and
        may be asserted that the `new` revision is already locked.

        If the `old` revision is `None`, then a new revision history will be
        created and the `new` revision is the origin revision.

        If the `old` revision is specified, the old revision's `__im_end_on__`
        date/time is set to the `new` revision's `__im_start_on__` date/time
        and the state is set to the `IM_STATE_RETIRED` state.
        """

    def rollbackToRevision(revision, activate=True):
        """Rollback to the given revision making it the newest one.

        Properly roll back to a previous revision.

        1. The revision must exist in the revision history. Otherwise a
           `KeyError` is raised.

        2. Find all revisions with a start timestamp greater than the
           revision's start timestamp.

           If no revisions are found, the revision is already the latest one.

           Remove all found revisions.

        3. If the `activate` flag is set, then set the revision's end
           timestamp should be set to None.
        """


class IRevisionedImmutable(IImmutable):
    """Revisioned Immutable Object

    This object represents one revision on an immutable object in the revision
    history of the immutable.

    While not strictly necessary, the revisioned immutable works best in
    combination with a manager. If `__im_manager__` is set, callbacks will
    be made to the manager to notify it of any new revisions using the
    `addRevision()` method.
    """

    __im_state__ = zope.schema.Choice(
        title=u'Immutable State',
        values=IM_STATES_REVISIONED,
        default=IM_STATE_TRANSIENT
    )

    __im_version__ = zope.schema.Int(
        title="Version",
        description=(
            "The version of the immutable revision. It is used to establish "
            "chronological order."
        ),
        default=0,
        required=True)

    __im_start_on__ = zope.schema.Datetime(
        title="Active Start Timestamp",
        description=(
            "Timestamp describing the moment at which the revision became "
            "active."
        ),
        required=True)

    __im_end_on__ = zope.schema.Datetime(
        title="Active End Timestamp",
        description=(
            "Timestamp describing the moment at which the revision retired. "
            "If the value is None, the revision is still active."
        ),
        required=False)

    __im_creator__ = zope.schema.TextLine(
        title="Revision Creator",
        description=(
            "A string representing the creator of the revision. It is up to "
            "the application to provide further meaning to this field."
            ),
        required=False)

    __im_comment__ = zope.schema.Datetime(
        title="Revision Comment",
        description="A himan readable comment of the revision.""",
        required=False)

    __im_manager__ = zope.schema.Object(
        title="Revisioned Immutable Manager",
        description=(
            "If set, callbacks will be made to notify the manager of "
            "changes."),
        schema=IRevisionedImmutableManager,
        required=False)

    def __im_update__(creator=None, comment=None):
        """Returns a context manager providing a clone that can be edited.

        If the immutable is already in the `transient` state, then the object
        itself is returned. All arguments to the method are ignored.

        If a clone is created, then the `__im_creator__` and `__im_commnet__`
        attributes will be set.

        If `__im_manager__` is set,
        `__im_manager__.addRevision(clone, old=self)` must be called.
        """
