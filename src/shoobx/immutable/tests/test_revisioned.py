###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""Revisioned Immutable Objects Tests."""

import datetime
import mock
import unittest
from zope.interface import verify

from shoobx.immutable import interfaces, revisioned


class DefaultRevisionInfoTest(unittest.TestCase):

    def test_attributes(self):
        info = revisioned.DefaultRevisionInfo()
        self.assertIsNone(info.creator)
        self.assertIsNone(info.comment)

    def test_setAttributes(self):
        info = revisioned.DefaultRevisionInfo()
        info.creator = 'arthur'
        info.comment = 'answer'
        self.assertEqual(info.creator, 'arthur')
        self.assertEqual(info.comment, 'answer')

    def test_defaultInfo(self):
        self.assertEqual(revisioned.DEFAULT_REVISION_INFO.creator, None)
        self.assertEqual(revisioned.DEFAULT_REVISION_INFO.comment, None)
        with revisioned.defaultInfo('arthur', 'answer') as info:
            self.assertEqual(info.creator, 'arthur')
            self.assertEqual(info.comment, 'answer')
            self.assertEqual(
                revisioned.DEFAULT_REVISION_INFO.creator, 'arthur')
            self.assertEqual(
                revisioned.DEFAULT_REVISION_INFO.comment, 'answer')

        self.assertEqual(revisioned.DEFAULT_REVISION_INFO.creator, None)
        self.assertEqual(revisioned.DEFAULT_REVISION_INFO.comment, None)

    def test_defaultInfo_nested(self):
        with revisioned.defaultInfo('arthur', 'question') as info:
            self.assertEqual(info.creator, 'arthur')
            self.assertEqual(info.comment, 'question')

            with revisioned.defaultInfo('computer', 'answer') as info:
                self.assertEqual(info.creator, 'computer')
                self.assertEqual(info.comment, 'answer')

            self.assertEqual(info.creator, 'arthur')
            self.assertEqual(info.comment, 'question')


class RevisionedImmutableBaseTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(
                interfaces.IRevisionedImmutable,
                revisioned.RevisionedImmutableBase))

    def test_init(self):
        with revisioned.RevisionedImmutableBase.__im_create__() as factory:
            im = factory()
        self.assertEqual(im.__im_version__, 0)
        self.assertIsNone(im.__im_start_on__)
        self.assertIsNone(im.__im_end_on__)
        self.assertIsNone(im.__im_creator__)
        self.assertIsNone(im.__im_comment__)
        self.assertIsNone(im.__im_manager__)

    def test_im_update(self):
        with revisioned.RevisionedImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__(creator='universe', comment='Get answer') as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertEqual(im2.answer, 42)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im2.__im_version__, 1)
        self.assertEqual(im2.__im_creator__, 'universe')
        self.assertEqual(im2.__im_comment__, 'Get answer')

    def test_im_update_withManager(self):
        with revisioned.RevisionedImmutableBase.__im_create__() as factory:
            im = factory()
        im.__im_manager__ = manager = mock.Mock()
        with im.__im_update__() as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertTrue(manager.addRevision.called)
        self.assertEqual(manager.addRevision.call_args, ((im2,), {'old': im}))

    def test_im_update_withDefaultInfo(self):
        with revisioned.RevisionedImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__(creator='universe', comment='Get answer') as im2:
            im2.answer = 42
        self.assertIsNot(im, im2)
        self.assertEqual(im2.answer, 42)
        self.assertEqual(im2.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertEqual(im2.__im_version__, 1)
        self.assertEqual(im2.__im_creator__, 'universe')
        self.assertEqual(im2.__im_comment__, 'Get answer')

    def test_im_update_withTransientImmutable(self):
        with revisioned.RevisionedImmutableBase.__im_create__(
                finalize=False) as factory:
            im = factory()
        with im.__im_update__() as im2:
            pass
        self.assertIs(im, im2)

    def test_im_update_withNestedUpdates(self):
        with revisioned.RevisionedImmutableBase.__im_create__() as factory:
            im = factory()
        with im.__im_update__() as im2:
            with im2.__im_update__() as im3:
                pass
        self.assertIsNot(im, im2)
        self.assertIsNot(im, im3)
        self.assertIs(im2, im3)

    def test_im_update_withSlave(self):
        with revisioned.RevisionedImmutableBase.__im_create__(
                mode=interfaces.IM_MODE_SLAVE) as factory:
            im = factory()
        with self.assertRaises(AttributeError):
            with im.__im_update__():
                pass

    def test_im_update_withException(self):
        with revisioned.RevisionedImmutableBase.__im_create__() as factory:
            im = factory()
        with self.assertRaises(RuntimeError):
            with im.__im_update__():
                raise RuntimeError(None)


class RevisionedImmutableTest(unittest.TestCase):

    def test_verifyInterface(self):
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

        with Answer.__im_create__() as factory:
            answer = factory()
        self.assertEqual(answer.__im_mode__, interfaces.IM_MODE_MASTER)
        self.assertEqual(answer.__im_state__, interfaces.IM_STATE_LOCKED)

        with Answer.__im_create__(
                finalize=False, mode=interfaces.IM_MODE_SLAVE) as factory:
            answer = factory()
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
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        self.assertIs(rimm.getCurrentRevision(), rim)

    def test_getCurrentRevision_noRevisions(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        self.assertIsNone(rimm.getCurrentRevision())

    def test_getCurrentRevision_noActiveLastRevisions(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        rim.__im_end_on__ = rim.__im_start_on__
        self.assertIsNone(rimm.getCurrentRevision())

    def test_getNumberOfRevisions(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        self.assertEqual(rimm.getNumberOfRevisions(), 0)
        rimm.addRevision(rim)
        self.assertEqual(rimm.getNumberOfRevisions(), 1)

    def test_getRevisionHistory(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        self.assertListEqual(list(rimm.getRevisionHistory()), [rim])

    def test_getRevisionHistory_withCreator(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        with rim.__im_update__(creator='someone') as rim2:
            pass
        self.assertListEqual(
            list(rimm.getRevisionHistory(creator='someone')), [rim2])

    def test_getRevisionHistory_withComment(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        with rim.__im_update__(comment='Some important update') as rim2:
            pass
        self.assertListEqual(
            list(rimm.getRevisionHistory(comment='important')), [rim2])

    def test_getRevisionHistory_withStartBefore(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rimm.now = lambda: datetime.datetime(2020, 1, 1)
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        rimm.now = now = lambda: datetime.datetime(2020, 1, 2)
        with rim.__im_update__(comment='Some important update'):
            pass
        self.assertListEqual(
            list(rimm.getRevisionHistory(startBefore=now())), [rim])

    def test_getRevisionHistory_withStartAfter(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rimm.now = now = lambda: datetime.datetime(2020, 1, 1)
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        rimm.now = lambda: datetime.datetime(2020, 1, 2)
        with rim.__im_update__(comment='Some important update') as rim2:
            pass
        self.assertListEqual(
            list(rimm.getRevisionHistory(startAfter=now())), [rim2])

    def test_getRevisionHistory_withReversed(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        with rim.__im_update__(creator='someone') as rim2:
            pass
        self.assertListEqual(
            list(rimm.getRevisionHistory(reversed=True)), [rim2, rim])

    def test_getRevisionHistory_withBatching(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)
        with rim.__im_update__(creator='someone') as rim2:
            pass
        with rim2.__im_update__(creator='someone') as rim3:
            pass
        with rim3.__im_update__(creator='someone') as rim4:
            pass
        with rim4.__im_update__(creator='someone'):
            pass
        self.assertListEqual(
            list(rimm.getRevisionHistory(batchSize=2)),
            [rim, rim2])
        self.assertListEqual(
            list(rimm.getRevisionHistory(batchStart=2, batchSize=2)),
            [rim3, rim4])

    def test_rollbackToRevision(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
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
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        with self.assertRaises(ValueError):
            rimm.rollbackToRevision(rim)

    def test_rollbackToRevision_noActivation(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
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

        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rimm.addRevision(rim)

        self.assertListEqual(rimm.__data__, [rim])
        self.assertIsNotNone(rim.__im_start_on__)
        self.assertIs(rim.__im_manager__, rimm)

    def test_addRevision_withOld(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            rim = factory()
        rim2 = rim.__im_clone__()
        rimm.addRevision(rim, old=rim2)
        self.assertListEqual(rimm.__data__, [rim])
        self.assertIsNotNone(rim.__im_start_on__)
        self.assertIs(rim.__im_manager__, rimm)
        self.assertIsNotNone(rim2.__im_end_on__)
        self.assertEqual(rim2.__im_state__, interfaces.IM_STATE_RETIRED)

    def test_addRevision_inTransientState(self):
        rimm = revisioned.SimpleRevisionedImmutableManager()
        rim = revisioned.RevisionedImmutable()
        self.assertNotEqual(rim.__im_state__, interfaces.IM_STATE_LOCKED)

        # Objects in a non-locked state *cannot* be added.
        with self.assertRaises(AssertionError):
            rimm.addRevision(rim)


class RevisionedMappingTest(unittest.TestCase):

    def test_init(self):
        map = revisioned.RevisionedMapping()
        self.assertDictEqual(map.__data__, {})

    def test_getRevisionManager(self):
        map = revisioned.RevisionedMapping()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            q1 = factory()
        map['q1'] = q1
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
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            q1 = factory()
        map['q1'] = q1
        self.assertListEqual(list(iter(map)), ['q1'])

    def test_getitem(self):
        map = revisioned.RevisionedMapping()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            q1 = factory()
        map['q1'] = q1
        self.assertIs(map['q1'], q1)

    def test_setitem(self):
        map = revisioned.RevisionedMapping()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            q1 = factory()
        map['q1'] = q1
        self.assertListEqual(map.__data__['q1'].__data__, [q1])

    def test_delitem(self):
        map = revisioned.RevisionedMapping()
        with revisioned.RevisionedImmutable.__im_create__() as factory:
            q1 = factory()
        map['q1'] = q1
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
        with self.Question.__im_create__() as factory:
            question = factory('The answer to everything')
        map['everything'] = question

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
        with question.__im_update__('computer', 'Provide Answer') as question2:
            question2.answer = 42

        # `question2` is now the current revision and has been added to the
        # container.
        self.assertEqual(question2.answer, 42)
        self.assertEqual(question2.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertIsNotNone(question2.__im_start_on__)
        self.assertIsNone(question2.__im_end_on__)
        self.assertIsNotNone(question2.__im_manager__)
        self.assertEqual(question2.__im_comment__, 'Provide Answer')
        self.assertEqual(question2.__im_creator__, 'computer')
        self.assertIs(map['everything'], question2)
        # The original question, on the other hand, has been retired.
        self.assertIsNotNone(question.__im_end_on__)
        self.assertEqual(question.__im_state__, interfaces.IM_STATE_RETIRED)
        self.assertIsNone(question.answer)

        # We can now also observe the revision history.
        revisions = map.getRevisionManager('everything')
        self.assertEqual(revisions.getNumberOfRevisions(), 2)
