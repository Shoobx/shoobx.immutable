=======
CHANGES
=======


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
