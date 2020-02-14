###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""Immutable Objects Tests."""

import datetime
import mock
import unittest
from zope.interface import verify

from shoobx.immutable import immutable, interfaces


class ImmutableHelpersTest(unittest.TestCase):

    def test_create(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        self.assertIsInstance(im, immutable.ImmutableBase)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_update(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with immutable.update(im) as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)

    def test_failOnNonTransient(self):
        func = mock.Mock()
        wrapper = immutable.failOnNonTransient(func)
        im = mock.Mock(__im_state__=interfaces.IM_STATE_TRANSIENT)
        wrapper(im)
        self.assertTrue(func.called)

    def test_failOnNonTransient_withLockedImmutable(self):
        func = mock.Mock()
        wrapper = immutable.failOnNonTransient(func)
        im = mock.Mock(__im_state__=interfaces.IM_STATE_LOCKED)
        with self.assertRaises(AttributeError):
            wrapper(im)


class ImmutableBaseTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableBase))

    def test_init(self):
        im = immutable.ImmutableBase()
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        with immutable.create(
                immutable.ImmutableBase, finalize=False) as factory:
            other = factory()
        conform = im.__im_conform__(other)
        self.assertIs(conform, other)
        self.assertEqual(conform.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(conform.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_conform_withLockedImmutable(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        with immutable.create(immutable.ImmutableBase) as factory:
            other = factory()
        comform = im.__im_conform__(other)
        self.assertIsNot(comform, other)
        self.assertEqual(comform.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(comform.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_conform_withCoreImmutable(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        other = 42
        self.assertIs(im.__im_conform__(other), other)

        other = datetime.date(2019, 6, 11)
        self.assertIs(im.__im_conform__(other), other)

        other = datetime.time(11, 3)
        self.assertIs(im.__im_conform__(other), other)

        other = datetime.datetime(2019, 6, 11, 11, 3)
        self.assertIs(im.__im_conform__(other), other)

        other = datetime.timedelta(days=42)
        self.assertIs(im.__im_conform__(other), other)

        other = datetime.tzinfo()
        self.assertIs(im.__im_conform__(other), other)

    def test_im_conform_withDict(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        im_dict = im.__im_conform__({'one': 1})
        self.assertDictEqual(dict(im_dict), {'one': 1})
        self.assertEqual(im_dict.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform_withList(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        im_list = im.__im_conform__(['one'])
        self.assertListEqual(list(im_list), ['one'])
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform_withSet(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        im_set = im.__im_conform__({'one'})
        self.assertSetEqual(set(im_set), {'one'})
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform_withConformableObject(self):

        class ConformedImmutable(immutable.ImmutableBase):
            pass

        class Mutable:
            def __im_get__(self, mode=None):
                with immutable.create(
                        ConformedImmutable, finalize=False, mode=mode) as fac:
                    return fac()

        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        im_mutable = im.__im_conform__(Mutable())
        self.assertEqual(im_mutable.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(im_mutable.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_conform_withNonConformableMutable(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
        with self.assertRaises(ValueError):
            im.__im_conform__(object())

    def test_im_clone(self):
        with immutable.create(
                immutable.ImmutableBase, finalize=False) as factory:
            im = factory()
        im2 = im.__im_clone__()
        self.assertIsNot(im, im2)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_clone_withLocked(self):
        with immutable.create(
                immutable.ImmutableBase, finalize=False) as factory:
            im = factory()
        im.__im_state__ = interfaces.IM_STATE_LOCKED
        # Clones are always transient.
        im2 = im.__im_clone__()
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_clone_withCoreSub(self):
        with immutable.create(
                immutable.ImmutableBase, finalize=False) as factory:
            im = factory()
        im.answer = 42
        # Clones are always transient.
        im2 = im.__im_clone__()
        self.assertEqual(im2.answer, 42)

    def test_im_clone_withImmutableSub(self):
        with immutable.create(immutable.ImmutableBase) as factory:
            im = factory()
            with immutable.ImmutableBase.__im_create__(
                    finalize=False) as factory:
                im.answer = factory()
        # All sub-objects of the clone are transient.
        im2 = im.__im_clone__()
        self.assertIsNot(im.answer, im2.answer)
        self.assertEqual(im2.answer.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_finalize(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        im.__im_finalize__()
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_finalize_withLockedObject(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with self.assertRaises(RuntimeError):
            im.__im_finalize__()

    def test_im_finalize_withCoreSub(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        im.answer = 42
        im.__im_finalize__()
        self.assertEqual(im.answer, 42)

    def test_im_finalize_withImmutableSub(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im.answer = factory()
        # finalization will finalize all sub-immutables as well.
        im.__im_finalize__()
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im.answer.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_before_update(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        # No-op.
        im.__im_before_update__(None)

    def test_im_create(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
            im.answer = 42

        self.assertEqual(im.answer, 42)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)

        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im2 = factory()
            im2.answer = 42

        self.assertEqual(im2.answer, 42)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)

        with immutable.ImmutableBase.__im_create__(
                mode=interfaces.IM_MODE_SLAVE) as factory:
            im3 = factory()
            im3.answer = 42

        self.assertEqual(im3.answer, 42)
        self.assertEqual(im3.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im3.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_create_factory_fails(self):
        class ImmutableFailure(immutable.ImmutableBase):
            def __im_after_create__(self, *args, **kw):
                raise ValueError('booooom')

        with ImmutableFailure.__im_create__() as factory:
            with self.assertRaises(ValueError):
                factory()

    def test_im_after_create(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        # No-op.
        im.__im_after_create__(None, foobar=42)

    def test_im_after_update(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        # No-op.
        im.__im_after_update__(None)

    def test_im_create_withoutFinalization(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_create_asSlave(self):
        with immutable.ImmutableBase.__im_create__(
                 mode=interfaces.IM_MODE_SLAVE) as factory:
            im = factory()
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_update(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertEqual(im2.answer, 42)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_update_withTransientImmutable(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        with im.__im_update__() as im2:
            pass
        self.assertIs(im, im2)

    def test_im_update_withNestedUpdates(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            with im2.__im_update__() as im3:
                pass
        self.assertIsNot(im, im2)
        self.assertIsNot(im, im3)
        self.assertIs(im2, im3)

    def test_im_update_withSlave(self):
        with immutable.ImmutableBase.__im_create__(
                mode=interfaces.IM_MODE_SLAVE) as factory:
            im = factory()
        with self.assertRaises(AttributeError):
            with im.__im_update__():
                pass

    def test_im_update_withException(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        with self.assertRaises(RuntimeError):
            with im.__im_update__():
                raise RuntimeError(None)

    def test_im_update_prohibitCrossRef(self):
        with immutable.ImmutableBase.__im_create__(finalize=False) as factory:
            im = factory()
        with im.__im_update__() as im2:
            with immutable.ImmutableBase.__im_create__(
                    finalize=False) as factory:
                im2.answer = factory()
            # Do not allow cross referenced objects
            with self.assertRaises(AssertionError):
                im2.other = {'answer': im2.answer}  # dict
            with self.assertRaises(AssertionError):
                im2.other = [im2.answer]  # list
            with self.assertRaises(AssertionError):
                im2.other = {im2.answer}  # set
            with self.assertRaises(AssertionError):
                im2.other = im2.answer  # as attribute

    def test_im_update_ensureImmutabilityOfOriginal(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__():
            with self.assertRaises(AttributeError):
                im.answer = 42

    def test_im_update_withImmutableSubojects(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            with immutable.ImmutableBase.__im_create__(
                    finalize=False) as factory:
                im2.question = factory()
                im2.question.answer = 42
        self.assertEqual(im2.question.answer, 42)
        # Make sure that all sub-objects get locked as well.
        self.assertEqual(im2.question.__im_state__, interfaces.IM_STATE_LOCKED)
        # Ensure that the question sub-object was cloned during the update.

    def test_im_update_ensureDeepClone(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            with immutable.ImmutableBase.__im_create__(
                    finalize=False) as factory:
                im2.question = factory()
        with im2.__im_update__() as im3:
            im3.question.answer = 42
        self.assertIsNot(im3.question, im2.question)

    def test_im_update_withImmutableFromAnotherUpdate(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with immutable.ImmutableBase.__im_create__() as factory:
            question = factory()
        with im.__im_update__() as im2:
            # One could argue that this assignment should not be allowed,
            # since we created the question immutable outside the
            # update. However, we create a clone of the immutable anyways,
            # since it is locked.
            im2.question = question
            im2.question.answer = 42
        self.assertIsNot(im2.question, question)
        self.assertEqual(im2.question.answer, 42)

    def test_im_update_disallowSubObjectUpdates(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            with immutable.ImmutableBase.__im_create__(
                    finalize=False) as factory:
                im2.question = factory()
        with self.assertRaises(AttributeError):
            with im2.question.__im_update__():
                pass

    def test_im_is_internal_attr(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        self.assertTrue(
            im.__im_is_internal_attr__('__answer__'))
        self.assertFalse(
            im.__im_is_internal_attr__('answer'))

    def test_setattr(self):
        # By default, the immutable is transient.
        im = immutable.ImmutableBase()
        im.answer = 42
        self.assertEqual(im.answer, 42)

    def test_setattr_withLockedImmutable(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        with self.assertRaises(AttributeError):
            im.answer = 42

    def test_setattr_withInternalAttribute(self):
        with immutable.ImmutableBase.__im_create__() as factory:
            im = factory()
        im.__answer__ = 42
        self.assertEqual(im.__answer__, 42)


class ImmutableTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.Immutable))

    def test_new(self):
        im = immutable.Immutable.__new__(immutable.Immutable)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init(self):

        class Answer(immutable.Immutable):
            pass

        with Answer.__im_create__() as factory:
            answer = factory()
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_LOCKED)

        with Answer.__im_create__(
                finalize=False, mode=interfaces.IM_MODE_SLAVE) as factory:
            answer = factory()
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init_withArgs(self):

        class Question(immutable.Immutable):

            def __init__(self, answer):
                self.answer = answer

        with Question.__im_create__() as factory:
            question = factory(42)
        self.assertEqual(question.answer, 42)
        self.assertEqual(question.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_LOCKED)

        with Question.__im_create__(
                finalize=False, mode=interfaces.IM_MODE_SLAVE) as factory:
            question = factory(42)
        self.assertEqual(question.answer, 42)
        self.assertEqual(question.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init_withMutableArgs(self):

        class Question(immutable.Immutable):

            def __init__(self, answers):
                self.answers = answers

        with Question.__im_create__() as factory:
            question = factory([42])
        self.assertIsInstance(question.answers, immutable.ImmutableList)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            question.answers.__im_state__, interfaces.IM_STATE_LOCKED)


class ImmutableDictTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableDict))

    def test_init(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withInitialDict(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory({'one': 1})
        self.assertDictEqual(dct.data, {'one': 1})
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withKeywordArgs(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(one=1)
        self.assertDictEqual(dct.data, {'one': 1})
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_clone(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory({'one': 1})
        dct = dct.__im_clone__()
        self.assertDictEqual(dct.data, {'one': 1})
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_clone_withImmutableValue(self):
        dct = {'question': {'answer': 42}}
        with immutable.ImmutableDict.__im_create__() as factory:
            im_dct = factory(dct)
        im_dct = im_dct.__im_clone__()
        self.assertIsInstance(
            im_dct['question'], immutable.ImmutableDict)
        self.assertEqual(
            im_dct['question'].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_dct.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_set_state(self):
        with immutable.ImmutableDict.__im_create__(finalize=False) as factory:
            im_dct = factory({'one': 1})
        self.assertEqual(im_dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_dct.__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_dct.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(im_dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_set_state_withImmutableValue(self):
        dct = {'question': {'answer': 42}}
        with immutable.ImmutableDict.__im_create__(finalize=False) as factory:
            im_dct = factory(dct)
        self.assertEqual(
            im_dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(
            im_dct.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(
            im_dct['question'].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_dct['question'].__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_dct.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            im_dct.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            im_dct['question'].__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_is_internal_attr(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        self.assertTrue(
            dct.__im_is_internal_attr__('__answer__'))
        self.assertTrue(
            dct.__im_is_internal_attr__('data'))
        self.assertFalse(
            dct.__im_is_internal_attr__('answer'))

    def test_attribute_setting(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        with self.assertRaises(AttributeError):
            dct.somethingNew = 42

        # XXX: do we allow this???
        #      pretty easy access
        dct.data['answer'] = 42
        dct.data = {}

        with dct.__im_update__() as dct2:
            # XXX: do we allow this???
            dct2.somethingNew = 42

        with self.assertRaises(AttributeError):
            dct2.somethingNew = 41

    def test_setitem(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        with dct.__im_update__() as dct2:
            dct2['answer'] = 42
        self.assertEqual(dct2['answer'], 42)
        with self.assertRaises(KeyError):
            dct['answer']

        with self.assertRaises(AttributeError):
            dct['answer'] = 42

    def test_setitem_withImmutable(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        with dct.__im_update__() as dct2:
            dct2['answer'] = item = immutable.ImmutableBase()
        self.assertIs(dct2['answer'], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_setitem_withImmutableSlave(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        with dct.__im_update__() as dct2:
            with immutable.ImmutableBase.__im_create__(
                    mode=interfaces.IM_MODE_SLAVE) as factory:
                item = factory()
            with self.assertRaises(AssertionError):
                dct2['answer'] = item

    def test_delitem(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42)
        with dct.__im_update__() as dct2:
            del dct2['answer']
        with self.assertRaises(KeyError):
            dct2['answer']
        self.assertEqual(dct['answer'], 42)

        with self.assertRaises(AttributeError):
            del dct['answer']

    def test_copy(self):
        # Copy works only on locked objects.
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42)
        im_dct_copy = dct.copy()
        self.assertDictEqual(dict(im_dct_copy), {'answer': 42})

        with self.assertRaises(AttributeError):
            im_dct_copy['fishes'] = 43

        with dct.__im_update__() as dct2:
            # We do not allow copy on a transient object, it just causes
            # headaches.
            with self.assertRaises(AssertionError):
                dct2.copy()

    def test_copy_withIImmutableObject(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        with AnImmutable.__im_create__() as factory:
            im2 = factory()
            im2.name = 'foobar'
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42, mutable=im2)
        dct.copy()  # this just does not fail

        with dct.__im_update__() as dct2:
            # we do not allow copy on a transient object, it just causes
            # headaches
            with self.assertRaises(AssertionError):
                dct2.copy()

    def test_clear(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42)
        with dct.__im_update__() as dct2:
            dct2.clear()
        self.assertDictEqual(dct.data, {'answer': 42})
        self.assertDictEqual(dct2.data, {})

        with self.assertRaises(AttributeError):
            dct.clear()

    def test_update(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        with dct.__im_update__() as dct2:
            dct2.update({'answer': 42})
        self.assertDictEqual(dct.data, {})
        self.assertDictEqual(dct2.data, {'answer': 42})

        with self.assertRaises(AttributeError):
            dct.update({})

    def test_setdefault(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory()
        with dct.__im_update__() as dct2:
            res = dct2.setdefault('answer', 42)
            self.assertEqual(res, 42)
        self.assertEqual(dct2['answer'], 42)
        with self.assertRaises(KeyError):
            dct['answer']

        with self.assertRaises(AttributeError):
            dct.setdefault('answer', 42)

    def test_pop(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42)
        with dct.__im_update__() as dct2:
            dct2.pop('answer')
        with self.assertRaises(KeyError):
            dct2['answer']
        self.assertEqual(dct['answer'], 42)

        with self.assertRaises(AttributeError):
            dct.pop('answer')

    def test_popitem(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42)
        with dct.__im_update__() as dct2:
            dct2.popitem()
        with self.assertRaises(KeyError):
            dct2['answer']
        self.assertEqual(dct['answer'], 42)

        with self.assertRaises(AttributeError):
            dct.popitem()

    def test_fromkeys(self):
        dct = immutable.ImmutableDict.fromkeys([41, 42], 'answer')
        self.assertEqual(dict(dct), {41: 'answer', 42: 'answer'})

    def test_fromkeys_withImmutables(self):
        with immutable.Immutable.__im_create__() as factory:
            im = factory()
        dct = immutable.ImmutableDict.fromkeys([41, 42], im)
        self.assertIsNot(dct[41], im)
        self.assertIsNot(dct[42], im)
        self.assertIsNot(dct[41], dct[42])

    def test_getstate(self):
        with immutable.ImmutableDict.__im_create__() as factory:
            dct = factory(answer=42)
        self.assertDictEqual(dct.__getstate__(), {'answer': 42})

    def test_setstate(self):
        dct = immutable.ImmutableDict.__new__(immutable.ImmutableDict)
        dct.__setstate__({'answer': 42})
        self.assertDictEqual(dict(dct), {'answer': 42})


class ImmutableSetTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableSet))

    def test_init(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory()
        self.assertEqual(im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withInitialSet(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({1})
        self.assertSetEqual(im_set.__data__, {1})
        self.assertEqual(im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_clone(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory([1])
        im_set = im_set.__im_clone__()
        self.assertSetEqual(im_set.__data__, {1})
        self.assertEqual(im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_clone_withImmutableValue(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory([{42}])
        im_set = im_set.__im_clone__()
        self.assertIsInstance(
            list(im_set)[0], immutable.ImmutableSet)
        self.assertEqual(
            list(im_set)[0].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_set_state(self):
        with immutable.ImmutableSet.__im_create__(finalize=False) as factory:
            im_set = factory({1})
        self.assertEqual(im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_set.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_set_state_withImmutableValue(self):
        with immutable.ImmutableSet.__im_create__(finalize=False) as factory:
            im_set = factory([{42}])
        self.assertEqual(
            im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(
            im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(
            list(im_set)[0].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            list(im_set)[0].__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_set.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            im_set.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            list(im_set)[0].__im_state__, interfaces.IM_STATE_LOCKED)

    def test_add(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory()
        with im_set.__im_update__() as im_set2:
            im_set2.add(42)
        self.assertSetEqual(im_set.__data__, set())
        self.assertSetEqual(im_set2.__data__, {42})

        with self.assertRaises(AttributeError):
            im_set2.add(41)

    def test_add_withImmutable(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory()
        with im_set.__im_update__() as im_set2:
            with immutable.ImmutableBase.__im_create__(
                    finalize=False) as factory:
                item = factory()
            im_set2.add(item)
        self.assertIs(list(im_set2)[0], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_add_withImmutableSlave(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory()
        with im_set.__im_update__() as im_set2:
            with self.assertRaises(AssertionError):
                with immutable.ImmutableBase.__im_create__(
                        mode=interfaces.IM_MODE_SLAVE) as factory:
                    item = factory()

                im_set2.add(item)

    def test_discard(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2.discard(42)
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.discard(42)

    # most methods are implemented in collections, and those call `add` and
    # `discard` but let's make sure that calling those higher level methods
    # work as expected, especially that they fail on non transient objects
    def test_remove(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2.remove(42)
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.remove(42)

    def test_pop(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            self.assertEqual(im_set2.pop(), 42)
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.pop()

    def test_clear(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2.clear()
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.clear()

    def test_ior(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2 |= {41}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, {41, 42})

        with self.assertRaises(AttributeError):
            im_set |= {41}

    def test_iand(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2 &= {41}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set &= {41}

    def test_ixor(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2 ^= {41}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, {41, 42})

        with self.assertRaises(AttributeError):
            im_set ^= {41}

    def test_isub(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        with im_set.__im_update__() as im_set2:
            im_set2 -= {42}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set -= {42}

    def test_contains(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        self.assertIn(42, im_set)

    def test_iter(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        self.assertEqual(list(iter(im_set)), [42])

    def test_len(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        self.assertEqual(len(im_set), 1)

    def test_repr(self):
        with immutable.ImmutableSet.__im_create__() as factory:
            im_set = factory({42})
        self.assertEqual(repr(im_set), '{42}')


class ImmutableListTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableList))

    def test_init(self):
        with immutable.ImmutableList.__im_create__() as factory:
            lst = factory()
        self.assertEqual(lst.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(lst.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withInitialList(self):
        with immutable.ImmutableList.__im_create__() as factory:
            lst = factory([42])
        self.assertListEqual(lst.data, [42])
        self.assertEqual(lst.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(lst.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_is_internal_attr(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im = factory()
        self.assertTrue(
            im.__im_is_internal_attr__('__answer__'))
        self.assertTrue(
            im.__im_is_internal_attr__('data'))
        self.assertFalse(
            im.__im_is_internal_attr__('answer'))

    def test_clone(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([42])
        im_list = im_list.__im_clone__()
        self.assertListEqual(im_list.data, [42])
        self.assertEqual(im_list.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_clone_withImmutableValue(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([[42]])
        im_list = im_list.__im_clone__()
        self.assertIsInstance(
            im_list[0], immutable.ImmutableList)
        self.assertEqual(
            im_list[0].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_set_state(self):
        with immutable.ImmutableList.__im_create__(finalize=False) as factory:
            im_list = factory([42])
        self.assertEqual(im_list.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_list.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_set_state_withImmutableValue(self):
        with immutable.ImmutableList.__im_create__(finalize=False) as factory:
            im_list = factory([[42]])
        self.assertEqual(
            im_list.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(
            im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(
            im_list[0].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_list[0].__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_list.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            im_list.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            im_list[0].__im_state__, interfaces.IM_STATE_LOCKED)

    def test_attribute_setting(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory()
        with self.assertRaises(AttributeError):
            im_list.somethingNew = 42

        # XXX: do we allow this???
        #      pretty easy access
        im_list.data.append(42)
        im_list.data = []

        with im_list.__im_update__() as im_list2:
            # XXX: do we allow this???
            im_list2.somethingNew = 42

        with self.assertRaises(AttributeError):
            im_list2.somethingNew = 41

    def test_setitem(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([None])
        with im_list.__im_update__() as im_list2:
            im_list2[0] = 42
        self.assertListEqual(im_list.data, [None])
        self.assertListEqual(im_list2.data, [42])

        with self.assertRaises(AttributeError):
            im_list[0] = 42

    def test_setitem_withImmutable(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([None])
        with im_list.__im_update__() as im_list2:
            im_list2[0] = item = immutable.ImmutableBase()
        self.assertIs(im_list2[0], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_setitem_withImmutableSlave(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([None])
        with im_list.__im_update__() as im_list2:
            with immutable.ImmutableBase.__im_create__(
                    mode=interfaces.IM_MODE_SLAVE) as factory:
                item = factory()
            with self.assertRaises(AssertionError):
                im_list2[0] = item

    def test_delitem(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([42])
        with im_list.__im_update__() as im_list2:
            del im_list2[0]
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            del im_list[0]

    def test_copy(self):
        # copy works on locked objects
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([41, 42])
        im_list_copy = im_list.copy()
        self.assertListEqual(im_list_copy.data, [41, 42])

        with self.assertRaises(AttributeError):
            im_list_copy.append(42)

        with im_list.__im_update__() as im_list2:
            # we do not allow copy on a transient object, it just causes
            # headaches
            with self.assertRaises(AssertionError):
                im_list2.copy()

    def test_copy_withMutable(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        with AnImmutable.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            im2.name = 'foobar'
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([41, 42, im2])
        im_list.copy()  # this just does not fail

        with im_list.__im_update__() as im_list2:
            # we do not allow copy on a transient object, it just causes
            # headaches
            with self.assertRaises(AssertionError):
                im_list2.copy()

    def test_append(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory()
        with im_list.__im_update__() as im_list2:
            im_list2.append(42)
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [42])

        with self.assertRaises(AttributeError):
            im_list.append(42)

    def test_extend(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory()
        with im_list.__im_update__() as im_list2:
            im_list2.extend([41, 42])
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [41, 42])

        with self.assertRaises(AttributeError):
            im_list.extend([41, 42])

    def test_add(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        with AnImmutable.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            im2.list = immutable.ImmutableList([41, 42]) + [44, 43]
            # make sure we get a transient result
            self.assertEqual(
                im2.list.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertListEqual(im2.list.data, [41, 42, 44, 43])

    def test_iadd(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory()
        with im_list.__im_update__() as im_list2:
            im_list2 += [41, 42]
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [41, 42])

        with self.assertRaises(AttributeError):
            im_list.extend([41, 42])

    def test_imul(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([41, 42])
        with im_list.__im_update__() as im_list2:
            im_list2 *= 2
        self.assertListEqual(im_list.data, [41, 42])
        self.assertListEqual(im_list2.data, [41, 42, 41, 42])

        with self.assertRaises(AttributeError):
            im_list.extend([41, 42])

    def test_imul_withImmutable(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        with AnImmutable.__im_create__() as factory:
            im2 = factory()

        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([41, 42, im2])
        with im_list.__im_update__() as im_list2:
            # fails because the list would end up with 2x AnImmutable
            # and we do not allow cross referenced objects
            with self.assertRaises(AssertionError):
                im_list2 *= 2

    def test_insert(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory()
        with im_list.__im_update__() as im_list2:
            im_list2.insert(0, 42)
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [42])

        with self.assertRaises(AttributeError):
            im_list.insert(0, 42)

    def test_insert_withImmutable(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory()
        with im_list.__im_update__() as im_list2:
            item = immutable.ImmutableBase()
            im_list2.insert(0, item)
        self.assertIs(im_list2[0], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_insert_withImmutableSlave(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([None])
        with im_list.__im_update__() as im_list2:
            with self.assertRaises(AssertionError):
                with immutable.ImmutableBase.__im_create__(
                        mode=interfaces.IM_MODE_SLAVE) as factory:
                    item = factory()

                im_list2.insert(0, item)

    def test_pop(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([42])
        with im_list.__im_update__() as im_list2:
            im_list2.pop()
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            im_list.pop()

    def test_remove(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([42])
        with im_list.__im_update__() as im_list2:
            im_list2.remove(42)
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            im_list.remove(42)

    def test_clear(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([42])
        with im_list.__im_update__() as im_list2:
            im_list2.clear()
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            im_list.clear()

    def test_reverse(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([41, 42])
        with im_list.__im_update__() as im_list2:
            im_list2.reverse()
        self.assertListEqual(im_list.data, [41, 42])
        self.assertListEqual(im_list2.data, [42, 41])

        with self.assertRaises(AttributeError):
            im_list.reverse()

    def test_sort(self):
        with immutable.ImmutableList.__im_create__() as factory:
            im_list = factory([43, 41, 42])
        with im_list.__im_update__() as im_list2:
            im_list2.sort()
        self.assertListEqual(im_list.data, [43, 41, 42])
        self.assertListEqual(im_list2.data, [41, 42, 43])

        with self.assertRaises(AttributeError):
            im_list.sort()
