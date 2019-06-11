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

    def test_update(self):
        im = immutable.ImmutableBase()
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

    def test_applyStateOnInit(self):
        func = mock.Mock()
        wrapper = immutable.applyStateOnInit(func)
        im = immutable.ImmutableBase.__new__(immutable.ImmutableBase)
        wrapper(im)
        self.assertTrue(func.called)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_applyStateOnInit_withoutFinalization(self):
        func = mock.Mock()
        wrapper = immutable.applyStateOnInit(func)
        im = immutable.ImmutableBase.__new__(immutable.ImmutableBase)
        wrapper(im, im_finalize=False)
        self.assertTrue(func.called)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_applyStateOnInit_asSlave(self):
        func = mock.Mock()
        wrapper = immutable.applyStateOnInit(func)
        im = immutable.ImmutableBase.__new__(immutable.ImmutableBase)
        wrapper(im, im_mode=interfaces.IM_MODE_SLAVE)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)


class ImmutableBaseTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableBase))

    def test_init(self):
        im = immutable.ImmutableBase()
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withoutFinalization(self):
        im = immutable.ImmutableBase(im_finalize=False)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init_asSlave(self):
        im = immutable.ImmutableBase(im_mode=interfaces.IM_MODE_SLAVE)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_conform(self):
        im = immutable.ImmutableBase()
        other = immutable.ImmutableBase(im_finalize=False)
        conform = im.__im_conform__(other)
        self.assertIs(conform, other)
        self.assertEqual(conform.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(conform.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_conform_withLockedImmutable(self):
        im = immutable.ImmutableBase()
        other = immutable.ImmutableBase()
        comform = im.__im_conform__(other)
        self.assertIsNot(comform, other)
        self.assertEqual(comform.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(comform.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_conform_withCoreImmutable(self):
        im = immutable.ImmutableBase()
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
        im = immutable.ImmutableBase()
        im_dict = im.__im_conform__({'one': 1})
        self.assertDictEqual(dict(im_dict), {'one': 1})
        self.assertEqual(im_dict.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform_withList(self):
        im = immutable.ImmutableBase()
        im_list = im.__im_conform__(['one'])
        self.assertListEqual(list(im_list), ['one'])
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform_withSet(self):
        im = immutable.ImmutableBase()
        im_set = im.__im_conform__({'one'})
        self.assertSetEqual(set(im_set), {'one'})
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_conform_withConformableObject(self):

        class ConformedImmutable(immutable.ImmutableBase):
            pass

        class Mutable:
            def __im_get__(self, mode=None):
                return ConformedImmutable(im_mode=mode, im_finalize=False)

        im = immutable.ImmutableBase()
        im_mutable = im.__im_conform__(Mutable())
        self.assertEqual(im_mutable.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertEqual(im_mutable.__im_mode__, interfaces.IM_MODE_SLAVE)

    def test_im_conform_withNonConformableMutable(self):
        im = immutable.ImmutableBase()
        with self.assertRaises(ValueError):
            im.__im_conform__(object())

    def test_im_clone(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im2 = im.__im_clone__()
        self.assertIsNot(im, im2)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_clone_withLocked(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im.__im_state__ = interfaces.IM_STATE_LOCKED
        # Clones are always transient.
        im2 = im.__im_clone__()
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_clone_withCoreSub(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im.answer = 42
        # Clones are always transient.
        im2 = im.__im_clone__()
        self.assertEqual(im2.answer, 42)

    def test_im_clone_withImmutableSub(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im.answer = immutable.ImmutableBase(im_finalize=False)
        im.__im_finalize__()
        # All sub-objects of the clone are transient.
        im2 = im.__im_clone__()
        self.assertIsNot(im.answer, im2.answer)
        self.assertEqual(im2.answer.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_finalize(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im.__im_finalize__()
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_finalize_withLockedObject(self):
        im = immutable.ImmutableBase()
        with self.assertRaises(RuntimeError):
            im.__im_finalize__()

    def test_im_finalize_withCoreSub(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im.answer = 42
        im.__im_finalize__()
        self.assertEqual(im.answer, 42)

    def test_im_finalize_withImmutableSub(self):
        im = immutable.ImmutableBase(im_finalize=False)
        im.answer = immutable.ImmutableBase(im_finalize=False)
        # finalization will finalize all sub-immutables as well.
        im.__im_finalize__()
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im.answer.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_before_update(self):
        im = immutable.ImmutableBase(im_finalize=False)
        # No-op.
        im.__im_before_update__(None)

    def test_im_after_update(self):
        im = immutable.ImmutableBase(im_finalize=False)
        # No-op.
        im.__im_after_update__(None)

    def test_im_update(self):
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertEqual(im2.answer, 42)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_update_withTransientImmutable(self):
        im = immutable.ImmutableBase(im_finalize=False)
        with im.__im_update__() as im2:
            pass
        self.assertIs(im, im2)

    def test_im_update_withNestedUpdates(self):
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            with im2.__im_update__() as im3:
                pass
        self.assertIsNot(im, im2)
        self.assertIsNot(im, im3)
        self.assertIs(im2, im3)

    def test_im_update_withSlave(self):
        im = immutable.ImmutableBase(im_mode=interfaces.IM_MODE_SLAVE)
        with self.assertRaises(AttributeError):
            with im.__im_update__() as im2:
                pass

    def test_im_update_withException(self):
        im = immutable.ImmutableBase()
        with self.assertRaises(RuntimeError):
            with im.__im_update__() as im2:
                raise RuntimeError(None)

    def test_im_update_prohibitCrossRef(self):
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            im2.answer = immutable.ImmutableBase()
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
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            with self.assertRaises(AttributeError):
                im.answer = 42

    def test_im_update_withImmutableSubojects(self):
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            im2.question = immutable.ImmutableBase()
            im2.question.answer = 42
        self.assertEqual(im2.question.answer, 42)
        # Make sure that all sub-objects get locked as well.
        self.assertEqual(im2.question.__im_state__, interfaces.IM_STATE_LOCKED)
        # Ensure that the question sub-object was cloned during the update.

    def test_im_update_ensureDeepClone(self):
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            im2.question = immutable.ImmutableBase()
        with im2.__im_update__() as im3:
            im3.question.answer = 42
        self.assertIsNot(im3.question, im2.question)

    def test_im_update_withImmutableFromAnotherUpdate(self):
        im = immutable.ImmutableBase()
        question = immutable.ImmutableBase()
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
        im = immutable.ImmutableBase()
        with im.__im_update__() as im2:
            im2.question = immutable.ImmutableBase()
        with self.assertRaises(AttributeError):
            with im2.question.__im_update__() as q3:
                pass

    def test_im_is_internal_attr(self):
        im = immutable.ImmutableBase()
        self.assertTrue(
            im.__im_is_internal_attr__('__answer__'))
        self.assertFalse(
            im.__im_is_internal_attr__('answer'))

    def test_setattr(self):
        # By default, the immutable is transient.
        im = immutable.ImmutableBase(im_finalize=False)
        im.answer = 42
        self.assertEqual(im.answer, 42)

    def test_setattr_withLockedImmutable(self):
        im = immutable.ImmutableBase()
        with self.assertRaises(AttributeError):
            im.answer = 42

    def test_setattr_withInternalAttribute(self):
        im = immutable.ImmutableBase()
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

        answer = Answer()
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_LOCKED)

        answer = Answer(
            im_finalize=False, im_mode=interfaces.IM_MODE_SLAVE)
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init_withArgs(self):

        class Question(immutable.Immutable):

            def __init__(self, answer):
                self.answer = answer

        question = Question(42)
        self.assertEqual(question.answer, 42)
        self.assertEqual(question.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_LOCKED)

        question = Question(
            42, im_finalize=False, im_mode=interfaces.IM_MODE_SLAVE)
        self.assertEqual(question.answer, 42)
        self.assertEqual(question.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init_withMutableArgs(self):

        class Question(immutable.Immutable):

            def __init__(self, answers):
                self.answers = answers

        question = Question([42])
        self.assertIsInstance(question.answers, immutable.ImmutableList)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(
            question.answers.__im_state__, interfaces.IM_STATE_LOCKED)


class ImmutableDictTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableDict))

    def test_init(self):
        dct = immutable.ImmutableDict()
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withInitialDict(self):
        dct = immutable.ImmutableDict({'one': 1})
        self.assertDictEqual(dct.data, {'one': 1})
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withKeywordArgs(self):
        dct = immutable.ImmutableDict(one=1)
        self.assertDictEqual(dct.data, {'one': 1})
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_clone(self):
        dct = immutable.ImmutableDict({'one': 1}).__im_clone__()
        self.assertDictEqual(dct.data, {'one': 1})
        self.assertEqual(dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(dct.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_clone_withImmutableValue(self):
        dct = {'question': {'answer': 42}}
        im_dct = immutable.ImmutableDict(dct).__im_clone__()
        self.assertIsInstance(
            im_dct['question'], immutable.ImmutableDict)
        self.assertEqual(
            im_dct['question'].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_dct.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_set_state(self):
        im_dct = immutable.ImmutableDict({'one': 1}, im_finalize=False)
        self.assertEqual(im_dct.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_dct.__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_dct.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(im_dct.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_set_state_withImmutableValue(self):
        dct = {'question': {'answer': 42}}
        im_dct = immutable.ImmutableDict(dct, im_finalize=False)
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
        im = immutable.ImmutableDict()
        self.assertTrue(
            im.__im_is_internal_attr__('__answer__'))
        self.assertTrue(
            im.__im_is_internal_attr__('data'))
        self.assertFalse(
            im.__im_is_internal_attr__('answer'))

    def test_attribute_setting(self):
        dct = immutable.ImmutableDict()
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
        dct = immutable.ImmutableDict()
        with dct.__im_update__() as dct2:
            dct2['answer'] = 42
        self.assertEqual(dct2['answer'], 42)
        with self.assertRaises(KeyError):
            dct['answer']

        with self.assertRaises(AttributeError):
            dct['answer'] = 42

    def test_setitem_withImmutable(self):
        dct = immutable.ImmutableDict()
        with dct.__im_update__() as dct2:
            dct2['answer'] = item = immutable.ImmutableBase(im_finalize=False)
        self.assertIs(dct2['answer'], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_setitem_withImmutableSlave(self):
        dct = immutable.ImmutableDict()
        with dct.__im_update__() as dct2:
            with self.assertRaises(AssertionError):
                dct2['answer'] = immutable.ImmutableBase(
                    im_mode=interfaces.IM_MODE_SLAVE)

    def test_delitem(self):
        dct = immutable.ImmutableDict(answer=42)
        with dct.__im_update__() as dct2:
            del dct2['answer']
        with self.assertRaises(KeyError):
            dct2['answer']
        self.assertEqual(dct['answer'], 42)

        with self.assertRaises(AttributeError):
            del dct['answer']

    def test_copy(self):
        # Copy works only on locked objects.
        dct = immutable.ImmutableDict(answer=42)
        im_dct_copy = dct.copy()
        self.assertDictEqual(dict(im_dct_copy), {'answer': 42})

        with self.assertRaises(AttributeError):
            im_dct_copy['fishes'] = 43

        with dct.__im_update__() as dct2:
            # We do not allow copy on a transient object, it just causes
            # headaches.
            with self.assertRaises(AssertionError):
                dct3 = dct2.copy()

    def test_copy_withIImmutableObject(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        im = AnImmutable()
        with im.__im_update__() as im2:
            im2.name = 'foobar'
        dct = immutable.ImmutableDict(answer=42, mutable=im2)
        dct_copy = dct.copy()

        with dct.__im_update__() as dct2:
            # we do not allow copy on a transient object, it just causes
            # headaches
            with self.assertRaises(AssertionError):
                dct3 = dct2.copy()

    def test_clear(self):
        dct = immutable.ImmutableDict(answer=42)
        with dct.__im_update__() as dct2:
            dct2.clear()
        self.assertDictEqual(dct.data, {'answer': 42})
        self.assertDictEqual(dct2.data, {})

        with self.assertRaises(AttributeError):
            dct.clear()

    def test_update(self):
        dct = immutable.ImmutableDict()
        with dct.__im_update__() as dct2:
            dct2.update({'answer': 42})
        self.assertDictEqual(dct.data, {})
        self.assertDictEqual(dct2.data, {'answer': 42})

        with self.assertRaises(AttributeError):
            dct.update({})

    def test_setdefault(self):
        dct = immutable.ImmutableDict()
        with dct.__im_update__() as dct2:
            res = dct2.setdefault('answer', 42)
            self.assertEqual(res, 42)
        self.assertEqual(dct2['answer'], 42)
        with self.assertRaises(KeyError):
            dct['answer']

        with self.assertRaises(AttributeError):
            dct.setdefault('answer', 42)

    def test_pop(self):
        dct = immutable.ImmutableDict(answer=42)
        with dct.__im_update__() as dct2:
            dct2.pop('answer')
        with self.assertRaises(KeyError):
            dct2['answer']
        self.assertEqual(dct['answer'], 42)

        with self.assertRaises(AttributeError):
            dct.pop('answer')

    def test_popitem(self):
        dct = immutable.ImmutableDict(answer=42)
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
        im = immutable.Immutable()
        dct = immutable.ImmutableDict.fromkeys([41, 42], im)
        self.assertIsNot(dct[41], im)
        self.assertIsNot(dct[42], im)
        self.assertIsNot(dct[41], dct[42])

    def test_getstate(self):
        dct = immutable.ImmutableDict(answer=42)
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
        set = immutable.ImmutableSet()
        self.assertEqual(set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(set.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withInitialSet(self):
        set = immutable.ImmutableSet({1})
        self.assertSetEqual(set.__data__, {1})
        self.assertEqual(set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(set.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_clone(self):
        im_set = immutable.ImmutableSet([1]).__im_clone__()
        self.assertSetEqual(im_set.__data__, {1})
        self.assertEqual(im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_clone_withImmutableValue(self):
        im_set = immutable.ImmutableSet([{42}]).__im_clone__()
        self.assertIsInstance(
            list(im_set)[0], immutable.ImmutableSet)
        self.assertEqual(
            list(im_set)[0].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_set_state(self):
        im_set = immutable.ImmutableSet({1}, im_finalize=False)
        self.assertEqual(im_set.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_set.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(im_set.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_set_state_withImmutableValue(self):
        im_set = immutable.ImmutableSet([{42}], im_finalize=False)
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
        im_set = immutable.ImmutableSet()
        with im_set.__im_update__() as im_set2:
            im_set2.add(42)
        self.assertSetEqual(im_set.__data__, set())
        self.assertSetEqual(im_set2.__data__, {42})

        with self.assertRaises(AttributeError):
            im_set2.add(41)

    def test_add_withImmutable(self):
        im_set = immutable.ImmutableSet()
        with im_set.__im_update__() as im_set2:
            item = immutable.ImmutableBase(im_finalize=False)
            im_set2.add(item)
        self.assertIs(list(im_set2)[0], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_add_withImmutableSlave(self):
        im_set = immutable.ImmutableSet()
        with im_set.__im_update__() as im_set2:
            with self.assertRaises(AssertionError):
                im_set2.add(immutable.ImmutableBase(
                    im_mode=interfaces.IM_MODE_SLAVE))

    def test_discard(self):
        im_set = immutable.ImmutableSet({42})
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
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            im_set2.remove(42)
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.remove(42)

    def test_pop(self):
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            self.assertEqual(im_set2.pop(), 42)
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.pop()

    def test_clear(self):
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            im_set2.clear()
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set.clear()

    def test_ior(self):
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            im_set2 |= {41}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, {41, 42})

        with self.assertRaises(AttributeError):
            im_set |= {41}

    def test_iand(self):
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            im_set2 &= {41}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set &= {41}

    def test_ixor(self):
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            im_set2 ^= {41}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, {41, 42})

        with self.assertRaises(AttributeError):
            im_set ^= {41}

    def test_isub(self):
        im_set = immutable.ImmutableSet({42})
        with im_set.__im_update__() as im_set2:
            im_set2 -= {42}
        self.assertSetEqual(im_set.__data__, {42})
        self.assertSetEqual(im_set2.__data__, set())

        with self.assertRaises(AttributeError):
            im_set -= {42}

    def test_contains(self):
        im_set = immutable.ImmutableSet({42})
        self.assertIn(42, im_set)

    def test_iter(self):
        im_set = immutable.ImmutableSet({42})
        self.assertEqual(list(iter(im_set)), [42])

    def test_len(self):
        im_set = immutable.ImmutableSet({42})
        self.assertEqual(len(im_set), 1)

    def test_repr(self):
        set = immutable.ImmutableSet({42})
        self.assertEqual(repr(set), '{42}')


class ImmutableListTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(interfaces.IImmutable, immutable.ImmutableList))

    def test_init(self):
        lst = immutable.ImmutableList()
        self.assertEqual(lst.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(lst.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_init_withInitialList(self):
        lst = immutable.ImmutableList([42])
        self.assertListEqual(lst.data, [42])
        self.assertEqual(lst.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(lst.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_is_internal_attr(self):
        im = immutable.ImmutableList()
        self.assertTrue(
            im.__im_is_internal_attr__('__answer__'))
        self.assertTrue(
            im.__im_is_internal_attr__('data'))
        self.assertFalse(
            im.__im_is_internal_attr__('answer'))

    def test_clone(self):
        im_list = immutable.ImmutableList([42]).__im_clone__()
        self.assertListEqual(im_list.data, [42])
        self.assertEqual(im_list.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_clone_withImmutableValue(self):
        im_list = immutable.ImmutableList([[42]]).__im_clone__()
        self.assertIsInstance(
            im_list[0], immutable.ImmutableList)
        self.assertEqual(
            im_list[0].__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(
            im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_im_set_state(self):
        im_list = immutable.ImmutableList([42], im_finalize=False)
        self.assertEqual(im_list.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_TRANSIENT)
        im_list.__im_set_state__(interfaces.IM_STATE_LOCKED)
        self.assertEqual(im_list.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_im_set_state_withImmutableValue(self):
        im_list = immutable.ImmutableList([[42]], im_finalize=False)
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
        im_list = immutable.ImmutableList()
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
        im_list = immutable.ImmutableList([None])
        with im_list.__im_update__() as im_list2:
            im_list2[0] = 42
        self.assertListEqual(im_list.data, [None])
        self.assertListEqual(im_list2.data, [42])

        with self.assertRaises(AttributeError):
            im_list[0] = 42

    def test_setitem_withImmutable(self):
        im_list = immutable.ImmutableList([None])
        with im_list.__im_update__() as im_list2:
            im_list2[0] = item = immutable.ImmutableBase(im_finalize=False)
        self.assertIs(im_list2[0], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_setitem_withImmutableSlave(self):
        im_list = immutable.ImmutableList([None])
        with im_list.__im_update__() as im_list2:
            with self.assertRaises(AssertionError):
                im_list2[0] = immutable.ImmutableBase(
                    im_mode=interfaces.IM_MODE_SLAVE)

    def test_delitem(self):
        im_list = immutable.ImmutableList([42])
        with im_list.__im_update__() as im_list2:
            del im_list2[0]
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            del im_list[0]

    def test_copy(self):
        # copy works on locked objects
        im_list = immutable.ImmutableList([41, 42])
        im_list_copy = im_list.copy()
        self.assertListEqual(im_list_copy.data, [41, 42])

        with self.assertRaises(AttributeError):
            im_list_copy.append(42)

        with im_list.__im_update__() as im_list2:
            # we do not allow copy on a transient object, it just causes
            # headaches
            with self.assertRaises(AssertionError):
                im_list3 = im_list2.copy()

    def test_copy_withMutable(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        im = AnImmutable()
        with im.__im_update__() as im2:
            im2.name = 'foobar'
        im_list = immutable.ImmutableList([41, 42, im2])
        im_list_copy = im_list.copy()

        with im_list.__im_update__() as im_list2:
            # we do not allow copy on a transient object, it just causes
            # headaches
            with self.assertRaises(AssertionError):
                im_list3 = im_list2.copy()

    def test_append(self):
        im_list = immutable.ImmutableList()
        with im_list.__im_update__() as im_list2:
            im_list2.append(42)
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [42])

        with self.assertRaises(AttributeError):
            im_list.append(42)

    def test_extend(self):
        im_list = immutable.ImmutableList()
        with im_list.__im_update__() as im_list2:
            im_list2.extend([41, 42])
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [41, 42])

        with self.assertRaises(AttributeError):
            im_list.extend([41, 42])

    def test_add(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        im = AnImmutable()
        with im.__im_update__() as im2:
            im2.list = immutable.ImmutableList([41, 42]) + [44, 43]
            # make sure we get a transient result
            self.assertEqual(
                im2.list.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertListEqual(im2.list.data, [41, 42, 44, 43])

    def test_iadd(self):
        im_list = immutable.ImmutableList()
        with im_list.__im_update__() as im_list2:
            im_list2 += [41, 42]
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [41, 42])

        with self.assertRaises(AttributeError):
            im_list.extend([41, 42])

    def test_imul(self):
        im_list = immutable.ImmutableList([41, 42])
        with im_list.__im_update__() as im_list2:
            im_list2 *= 2
        self.assertListEqual(im_list.data, [41, 42])
        self.assertListEqual(im_list2.data, [41, 42, 41, 42])

        with self.assertRaises(AttributeError):
            im_list.extend([41, 42])

    def test_imul_withImmutable(self):
        class AnImmutable(immutable.ImmutableBase):
            pass

        im_list = immutable.ImmutableList([41, 42, AnImmutable()])
        with im_list.__im_update__() as im_list2:
            # fails because the list would end up with 2x AnImmutable
            # and we do not allow cross referenced objects
            with self.assertRaises(AssertionError):
                im_list2 *= 2

    def test_insert(self):
        im_list = immutable.ImmutableList()
        with im_list.__im_update__() as im_list2:
            im_list2.insert(0, 42)
        self.assertListEqual(im_list.data, [])
        self.assertListEqual(im_list2.data, [42])

        with self.assertRaises(AttributeError):
            im_list.insert(0, 42)

    def test_insert_withImmutable(self):
        im_list = immutable.ImmutableList()
        with im_list.__im_update__() as im_list2:
            item = immutable.ImmutableBase(im_finalize=False)
            im_list2.insert(0, item)
        self.assertIs(im_list2[0], item)
        self.assertEqual(item.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_insert_withImmutableSlave(self):
        im_list = immutable.ImmutableList([None])
        with im_list.__im_update__() as im_list2:
            with self.assertRaises(AssertionError):
                im_list2.insert(0, immutable.ImmutableBase(
                    im_mode=interfaces.IM_MODE_SLAVE))

    def test_pop(self):
        im_list = immutable.ImmutableList([42])
        with im_list.__im_update__() as im_list2:
            im_list2.pop()
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            im_list.pop()

    def test_remove(self):
        im_list = immutable.ImmutableList([42])
        with im_list.__im_update__() as im_list2:
            im_list2.remove(42)
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            im_list.remove(42)

    def test_clear(self):
        im_list = immutable.ImmutableList([42])
        with im_list.__im_update__() as im_list2:
            im_list2.clear()
        self.assertListEqual(im_list.data, [42])
        self.assertListEqual(im_list2.data, [])

        with self.assertRaises(AttributeError):
            im_list.clear()

    def test_reverse(self):
        im_list = immutable.ImmutableList([41, 42])
        with im_list.__im_update__() as im_list2:
            im_list2.reverse()
        self.assertListEqual(im_list.data, [41, 42])
        self.assertListEqual(im_list2.data, [42, 41])

        with self.assertRaises(AttributeError):
            im_list.reverse()

    def test_sort(self):
        im_list = immutable.ImmutableList([43, 41, 42])
        with im_list.__im_update__() as im_list2:
            im_list2.sort()
        self.assertListEqual(im_list.data, [43, 41, 42])
        self.assertListEqual(im_list2.data, [41, 42, 43])

        with self.assertRaises(AttributeError):
            im_list.sort()
