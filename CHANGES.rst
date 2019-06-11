=======
CHANGES
=======


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
