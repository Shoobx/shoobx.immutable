=======
CHANGES
=======


2.0.1 (2020-04-23)
------------------

- Allow ``defaultInfo()`` decorator to be nested.


2.0.0 (2020-04-21)
------------------

- IMPORTANT: Add immutable state as a column to the table. This will require a
  migration of your database schema and data.

- Introduced new ``IM_STATE_DELETED`` state which marks an object as deleted.

- Add new ``_pj_with_deleted_items`` flag that when set will change the
  container API to return deleted items as well.

- Added ``ImmutableContainer.withDeletedItems()`` method that will clone the
  container and set the ``_pj_with_deleted_items`` flag. That will by
  definition reset all caches to prohibit inconsistent results.

- The ``test_functional_deletionAndRevival()`` demonstrates the deletion and
  revivial functionality.


1.5.0 (2020-04-20)
------------------

- Honor the ``_pj_remove_documents`` flag in the pjpersist
  ``ImmutableContainer`` by simply marking the last version of the object as
  retired and assigning an end date. This way deletions can be undone. Also,
  audit logs can now be complete.

- Allow the creator and comment to be specified globally, so that APIs don't
  have to carry that information through all the layers.


1.4.3 (2020-02-22)
------------------

- Make sure that `ImmutableContainer` does not accept transient objects. This
  is particularly important since objects can be initialized in transient
  state when not using the `create()` context manager. It also protects the
  object from being updated in a container before completing its update.

- Refactored `__delitem__` tests to be more minimal and document the use cases
  more clearly.


1.4.2 (2020-02-15)
------------------

- 1.4.1 was a brown bag release.


1.4.1 (2020-02-15)
------------------

- Missed to re-export `shoobx.immutable.immutable.create`


1.4.0 (2020-02-14)
------------------

- Changed the pattern of creating an immutable object to a context manager.
  NOTE, just creating an object like `Immutable()` will give you a transient
  object.
  The preferred pattern is:

  >>> import shoobx.immutable as im
  >>> with im.create(im.Immutable) as factory:
  ...     imObj = factory()

  This makes it way easier to set initial attributes.
  See README.rst and docs and tests for details.


1.3.1 (2020-02-10)
------------------

- Fixing leftover `_pj_get_resolve_filter` occurrences in `ImmutableContainer`


1.3.0 (2020-02-06)
------------------

- Fix `ImmutableContainer.__delitem__` : In order to delete all revisions of
  an object, the delete method used an internal super() call to get query
  filters. That ended up ignoring subclass filters causing deletes across
  contianer boundaries.

  As a solution, a new `_pj_get_resolve_filter_all_versions` method has been
  introduced to return a query for all versions within a container. The
  `_pj_get_resolve_filter` method now uses the other one and simply adds the
  "latest version" constraint. All sub-containers should now override
  `_pj_get_resolve_filter_all_versions` instead of `_pj_get_resolve_filter`.


1.2.1 (2020-02-02)
------------------

- Fix `ImmutableContainer.__delitem__` : it did not remove revisions of the
  deleted object

- Fix `ImmutableContainer.rollbackToRevision` : it rolled back ALL objects
  to the given revision


1.2.0 (2020-01-20)
------------------

- Extended `IRevisionedImmutableManager` to support efficient version
  management.

  * Added `getNumberOfRevisions(obj)` method to return the number of revisions
    available for a given object. Note that this does not necessarily equal to
    the latest revision number.

  * Exended `getRevisionHistory()` with multiple new arguments to support
    filtering, sorting and batching:

    Filter Arguments:

    * `creator`: The creator of the revision must match the argument.

    * `comment`: The comment must contain the argument as a substring.

    * `startBefore`: The revision must start before the given date/time.

    * `startAfter`: The revision must start after the given date/time.

    Ordering Arguments:

    * `reversed`: When true, the history will be return in reverse
                  chronological order, specifically the latest revision is
                  listed first.

    Batching Arguments:

    * `batchStart`: The index at which to start the batch.

    * `batchSize`: The size the of the batch. It is thus the max length of
                   the iterable.

- Provided an implementation of the new arguments for both the simple revision
  manage and the pjpersist container.

- Declare that `ImmutableContainer` implements `IRevisionedImmutableManager`.

- Increased test coverage back to 100%.


1.1.1 (2019-06-11)
------------------

- Added `datetime` classes as system immutable types.


1.1.0 (2019-05-31)
------------------

- Introduced `__im_version__` to `IRevisionedImmutable` and use it instead of
  timestamps to create a chronological order of revisions. (Timestamps might be
  slightly different accross servers and cause bad history.)

- Do not duplicate implementation of `__im_update__()` in
  `RevisionedImmutableBase`. Use `__im_[before|after]_update__()` to do all
  revision-related tasks.

- Tweak `copy()` implementation for `ImmutableList` and `ImmutableDict`.

- Properly implement `ImmutableDict.fromkeys()`.


1.0.5 (2019-05-31)
------------------

- Fix `ImmutableList.copy()` to just work when locked. This allows for only
  making a shallow clone, since any update will cause a deep copy and thus
  immutability is guaranteed.

- Implemented `ImmutableDict.copy()`. Raise error on `ImmutableDict.fromkeys()`.

- `ImmutableContainer` also needs an updated `_pj_column_fields` list.

- Minor test fixes.

- Minor documentation fixes and code comment enhancements.


1.0.4 (2019-05-30)
------------------

- Add API documentation.


1.0.3 (2019-05-30)
------------------

- Moved documentation to Read the Docs.


1.0.2 (2019-05-30)
------------------

- Add some readable documentation.

- Added high-level `shoobx.immutable.update(im, *args, **kw)` function.

- Implemented `__repr__()` for `ImmutableSet` to mimic behavior of
  `ImmutableDict` and `ImmutableList`.


1.0.1 (2019-05-30)
------------------

- Fix package description.


1.0.0 (2019-05-30)
------------------

- Immutable Types, Immutable Dict, Immutable Set, Immutable List

- Revisioned Immutable with Revision Manager sample implementation

- Optional: pjpersist support for immutables. Requires pjpersist>=1.7.0.

- Initial Release
