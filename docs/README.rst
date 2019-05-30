================
Using Immutables
================

Immutable objects can make certain complex systems more reasonable, because they
tightly control when an object is modified and how. It also guarantees that an
object can never change for another accessor in a different subsystem.

Introduction
------------

Let's start with a simple dictionary:

  >>> import shoobx.immutable as im
  >>> answer = im.ImmutableDict({
  ...     'question': 'Answer to the ultimate question of life, ...',
  ...     'answer': 0
  ... })

  >>> answer['answer']
  0

But no value can be changed anymore:

  >>> answer['answer'] = 42
  Traceback (most recent call last):
  ...
  AttributeError: Cannot update locked immutable object.

Immutable objects are updated through a special context manager that creates a
new version of the object that can be modified within the context manager
block.

  >>> orig = answer
  >>> with im.update(answer) as answer:
  ...     answer['answer'] = 42

  >>> answer['answer']
  42

Note that the `answer` dictionary is a completely new object and that the
original object is still unmodified.

  >>> orig is not answer
  True
  >>> orig['answer']
  0

Of course we can also create complex object structures, for example by adding
a list:

  >>> with im.update(answer) as answer:
  ...     answer['witnesses'] = ['Arthur', 'Gag']

  >>> answer['witnesses']
  ['Arthur', 'Gag']

Of course, the list has been converted to its immutable equal, so that items
cannot be modified.

  >>> isinstance(answer['witnesses'], im.ImmutableList)
  True
  >>> answer['witnesses'].append('Deep Thought')
  Traceback (most recent call last):
  ...
  AttributeError: Cannot update locked immutable object.

However, updating from an child/sub-object is not allowed, since creating a
new version of a child would sematically modify its parent thus violating the
immutability constraint:

  >>> with im.update(answer['witnesses']) as witnesses:
  ...     pass
  Traceback (most recent call last):
  ...
  AttributeError: update() is only available for master immutables.

The system accomplishes this by assigning "master" and "slave" modes to the
immutables. The root immutable is the master and any sub-objects below are
slaves.

Immutable sets are also supported as a core immutable:

  >>> data = im.ImmutableSet({6})
  >>> data
  {6}

  >>> with im.update(data) as data:
  ...     data.discard(6)
  ...     data.add(9)
  >>> data
  {9}


Custom Immutables
-----------------

Creating your own immutable objects is simple:

  >>> class Answer(im.Immutable):
  ...     def __init__(self, question=None, answer=None, witnesses=None):
  ...         self.question = question
  ...         self.answer = answer
  ...         self.witnesses = witnesses

  >>> answer = Answer('The Answer', 42, ['Arthur', 'Gag'])
  >>> answer.answer
  42

Note how the list is automatically converted to its immutable equivalent:

  >>> isinstance(answer.witnesses, im.ImmutableList)
  True

Of course you cannot modify an immutable other than the update context:

  >>> answer.answer = 54
  Traceback (most recent call last):
  ...
  AttributeError: Cannot update locked immutable object.

  >>> with im.update(answer) as answer:
  ...     answer.answer = 54
  >>> answer.answer
  54


Revisioned Immutables
---------------------

Since mutables create a new object for every change, they are ideal for
creating systems that have to keep track of their entire history. This package
provides support for such systems by defining a revision manager API and
revisioned immutable that are managed within it.

Let's start by creating a custom revisioned immutable:

  >>> class Answer(im.RevisionedImmutable):
  ...
  ...     def __init__(self, question=None, answer=None):
  ...         self.question = question
  ...         self.answer = answer

A simple implementation of the revision manager API is provided to demonstrate
a possible implementation path.

  >>> data = im.RevisionedMapping()
  >>> data['a'] = answer = Answer('Answer to the ultimate question')

The answer is the current revision and has been added to the
manager.

  >>> data['a'] is answer
  True

In addition to the usual immutability features, the Revisioned
immutable has several additional attributes that help with the management of
the revisions:

  >>> answer.__im_start_on__
  datetime.datetime(...)
  >>> answer.__im_end_on__ is None
  True
  >>> answer.__im_manager__
  <shoobx.immutable.revisioned.SimpleRevisionedImmutableManager ...>
  >>> answer.__im_creator__ is None
  True
  >>> answer.__im_comment__ is None
  True

The update API is extended to support setting the creator and comment of the
change:

  >>> answer_r1 = answer
  >>> with im.update(answer, 'universe', 'Provide Answer') as answer:
  ...     answer.answer = 42

We now have a second revision of the answer that has the comemnt and creator
set:

  >>> answer.answer
  42

  >>> answer.__im_start_on__
  datetime.datetime(...)
  >>> answer.__im_end_on__ is None
  True
  >>> answer.__im_creator__
  'universe'
  >>> answer.__im_comment__
  'Provide Answer'

The first revision is now retired and has an end date/time (which equals the
start date/time of the new revision):

  >>> answer_r1.__im_start_on__
  datetime.datetime(...)
  >>> answer_r1.__im_end_on__ == answer.__im_start_on__
  True
  >>> answer_r1.__im_state__ == im.interfaces.IM_STATE_RETIRED
  True

The manager has APIs to manage the various revisions.

  >>> revisions = data.getRevisionManager('a')
  >>> len(revisions.getRevisionHistory())
  2

  >>> revisions.getCurrentRevision(answer_r1) is answer
  True

We can even roll back to a previous revision:

  >>> revisions.rollbackToRevision(answer_r1)

  >>> len(revisions.getRevisionHistory())
  1
  >>> answer_r1.__im_end_on__ is None
  True
  >>> answer_r1.__im_state__ == im.interfaces.IM_STATE_LOCKED
  True


Optional `pjpersist` Support
----------------------------

A more serious and production-ready implementation of the revision manager API
is provided in `shoobx.immutable.pjpersist` which utilizes `pjpersist` to
store all data.


Notes
-----

A technical discussion on the system's inner workings is located in the
doc strings of the corresponding interfaces. In addition, the tests covera a
lot of special cases not dicsussed here.
