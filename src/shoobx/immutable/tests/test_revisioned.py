###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""Revisioned Immutable Objects Tests."""

import mock
import unittest
from zope.interface import verify

from shoobx.immutable import interfaces, revisioned


class RevisionedImmutableBaseTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(
                interfaces.IImmutable,
                revisioned.RevisionedImmutableBase))
        self.assertTrue(
            verify.verifyClass(
                interfaces.IRevisionedImmutable,
                revisioned.RevisionedImmutableBase))

    def test_init(self):
        rim = revisioned.RevisionedImmutableBase()
        self.assertEqual(rim.__im_version__, 0)
        self.assertIsNone(rim.__im_start_on__)
        self.assertIsNone(rim.__im_end_on__)
        self.assertIsNone(rim.__im_creator__)
        self.assertIsNone(rim.__im_comment__)
        self.assertIsNone(rim.__im_manager__)

    def test_im_update(self):
        im = revisioned.RevisionedImmutableBase()
        with im.__im_update__(creator='universe', comment='Get answer') as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertEqual(im2.answer, 42)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im2.__im_version__, 1)
        self.assertEqual(im2.__im_creator__, 'universe')
        self.assertEqual(im2.__im_comment__, 'Get answer')

    def test_im_update_withManager(self):
        im = revisioned.RevisionedImmutableBase()
        im.__im_manager__ = manager = mock.Mock()
        with im.__im_update__() as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertTrue(manager.addRevision.called)
        self.assertEqual(manager.addRevision.call_args, ((im2,), {'old': im}))

    def test_im_update_withTransientImmutable(self):
        im = revisioned.RevisionedImmutableBase(im_finalize=False)
        with im.__im_update__() as im2:
            pass
        self.assertIs(im, im2)

    def test_im_update_withNestedUpdates(self):
        im = revisioned.RevisionedImmutableBase()
        with im.__im_update__() as im2:
            with im2.__im_update__() as im3:
                pass
        self.assertIsNot(im, im2)
        self.assertIsNot(im, im3)
        self.assertIs(im2, im3)

    def test_im_update_withSlave(self):
        im = revisioned.RevisionedImmutableBase(
            im_mode=interfaces.IM_MODE_SLAVE)
        with self.assertRaises(AttributeError):
            with im.__im_update__() as im2:
                pass

    def test_im_update_withException(self):
        im = revisioned.RevisionedImmutableBase()
        with self.assertRaises(RuntimeError):
            with im.__im_update__() as im2:
                raise RuntimeError(None)


class RevisionedImmutableTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(
                interfaces.IImmutable,
                revisioned.RevisionedImmutable))
        self.assertTrue(
            verify.verifyClass(
                interfaces.IRevisionedImmutable,
                revisioned.RevisionedImmutable))

    def test_new(self):
        im = revisioned.RevisionedImmutable.__new__(
            revisioned.RevisionedImmutable)
        self.assertEqual(im.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(im.__im_state__, interfaces.IM_STATE_TRANSIENT)

    def test_init(self):

        class Question(revisioned.RevisionedImmutable):

            def __init__(self, answer):
                self.answer = answer

        class Answer(revisioned.RevisionedImmutable):
            # omit __init__ here
            pass

        question = Question(42)
        self.assertEqual(question.answer, 42)
        self.assertEqual(question.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_LOCKED)

        question = Question(
            42, im_finalize=False, im_mode=interfaces.IM_MODE_SLAVE)
        self.assertEqual(question.answer, 42)
        self.assertEqual(question.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_TRANSIENT)

        answer = Answer()
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_LOCKED)

        answer = Answer(
            im_finalize=False, im_mode=interfaces.IM_MODE_SLAVE)
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_SLAVE)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_TRANSIENT)


class SimpleRevisionedImmutableManagerTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(
                interfaces.IRevisionedImmutableManager,
                revisioned.SimpleRevisionedImmutableManager))

    def test_init(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        self.assertListEqual(rimm.__data__, [])

    def test_getCurrentRevision(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rimm.addRevision(rim)
        self.assertIs(rimm.getCurrentRevision(), rim)

    def test_getCurrentRevision_noRevisions(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        self.assertIsNone(rimm.getCurrentRevision())

    def test_getCurrentRevision_noActiveLastRevisions(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rimm.addRevision(rim)
        rim.__im_end_on__ = rim.__im_start_on__
        self.assertIsNone(rimm.getCurrentRevision())

    def test_getRevisionHistory(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rimm.addRevision(rim)
        self.assertListEqual(rimm.getRevisionHistory(), [rim])

    def test_rollbackToRevision(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rimm.addRevision(rim)
        with rim.__im_update__() as rim2:
            pass
        self.assertListEqual(rimm.__data__, [rim, rim2])
        self.assertIsNotNone(rim.__im_end_on__)
        self.assertEqual(rim.__im_state__, interfaces.IM_STATE_RETIRED)
        rimm.rollbackToRevision(rim)
        self.assertListEqual(rimm.__data__, [rim])
        self.assertIsNone(rim.__im_end_on__)
        self.assertEqual(rim.__im_state__, interfaces.IM_STATE_LOCKED)

    def test_rollbackToRevision_unknownRevision(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        with self.assertRaises(ValueError):
            rimm.rollbackToRevision(rim)

    def test_rollbackToRevision_noActivation(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rimm.addRevision(rim)
        with rim.__im_update__() as rim2:
            pass
        self.assertListEqual(rimm.__data__, [rim, rim2])
        self.assertIsNotNone(rim.__im_end_on__)
        self.assertEqual(rim.__im_state__, interfaces.IM_STATE_RETIRED)
        rimm.rollbackToRevision(rim, activate=False)
        self.assertListEqual(rimm.__data__, [rim])
        self.assertIsNotNone(rim.__im_end_on__)
        self.assertEqual(rim.__im_state__, interfaces.IM_STATE_RETIRED)

    def test_addRevision(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rimm.addRevision(rim)
        self.assertListEqual(rimm.__data__, [rim])
        self.assertIsNotNone(rim.__im_start_on__)
        self.assertIs(rim.__im_manager__, rimm)

    def test_addRevision_withOld(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        rim2 = rim.__im_clone__()
        rimm.addRevision(rim, old=rim2)
        self.assertListEqual(rimm.__data__, [rim])
        self.assertIsNotNone(rim.__im_start_on__)
        self.assertIs(rim.__im_manager__, rimm)
        self.assertIsNotNone(rim2.__im_end_on__)
        self.assertEqual(rim2.__im_state__, interfaces.IM_STATE_RETIRED)


class RevisionedMappingTest(unittest.TestCase):

    def test_init(self):
        map = revisioned.RevisionedMapping()
        self.assertDictEqual(map.__data__, {})

    def test_getRevisionManager(self):
        map = revisioned.RevisionedMapping()
        map['q1'] = q1 = revisioned.RevisionedImmutable()
        rimm = map.getRevisionManager('q1')
        self.assertIn(q1, rimm.__data__)

    def test_getRevisionManager_withUnknownKey(self):
        map = revisioned.RevisionedMapping()
        with self.assertRaises(KeyError):
            map.getRevisionManager('q1')

    def test_len(self):
        map = revisioned.RevisionedMapping()
        self.assertEqual(len(map), 0)

    def test_iter(self):
        map = revisioned.RevisionedMapping()
        map['q1'] = revisioned.RevisionedImmutable()
        self.assertListEqual(list(iter(map)), ['q1'])

    def test_getitem(self):
        map = revisioned.RevisionedMapping()
        map['q1'] = q1 = revisioned.RevisionedImmutable()
        self.assertIs(map['q1'], q1)

    def test_setitem(self):
        map = revisioned.RevisionedMapping()
        map['q1'] = q1 = revisioned.RevisionedImmutable()
        self.assertListEqual(map.__data__['q1'].__data__, [q1])

    def test_delitem(self):
        map = revisioned.RevisionedMapping()
        map['q1'] = revisioned.RevisionedImmutable()
        self.assertIn('q1', map.__data__)
        del map['q1']
        self.assertNotIn('q1', map.__data__)


class RevisionedFunctionalTest(unittest.TestCase):

    class Question(revisioned.RevisionedImmutable):
        question = None
        answer = None

        def __init__(self, question=None, answer=None):
            self.question = question
            self.answer = answer

    def test_functional(self):
        map = revisioned.RevisionedMapping()
        map['everything'] = question = self.Question('The answer to everything')

        # The question is the current revision and has been added to the
        # container.
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertIsNotNone(question.__im_start_on__)
        self.assertIsNone(question.__im_end_on__)
        self.assertIsNotNone(question.__im_manager__)
        self.assertIsNone(question.__im_comment__)
        self.assertIsNone(question.__im_creator__)
        self.assertIs(map['everything'], question)

        # Now we modify the question.
        with question.__im_update__('srichter', 'Provide Answer') as question2:
            question2.answer = 42

        # `question2` is now the current revision and has been added to the
        # container.
        self.assertEqual(question2.answer, 42)
        self.assertEqual(question2.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertIsNotNone(question2.__im_start_on__)
        self.assertIsNone(question2.__im_end_on__)
        self.assertIsNotNone(question2.__im_manager__)
        self.assertEqual(question2.__im_comment__, 'Provide Answer')
        self.assertEqual(question2.__im_creator__, 'srichter')
        self.assertIs(map['everything'], question2)
        # The original question, on the other hand, has been retired.
        self.assertIsNotNone(question.__im_end_on__)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_RETIRED)
        self.assertIsNone(question.answer)

        # We can now also observe the revision history.
        revisions = map.getRevisionManager('everything')
        self.assertTrue(len(revisions.getRevisionHistory()), 2)
