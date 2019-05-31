###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""shoobx.app revisioned immutables.
"""
import datetime
import mock
import pjpersist.interfaces as pjinterfaces
import transaction
import unittest
import zope.component
import zope.interface
import zope.schema
from pjpersist import datamanager, serialize, testing
from zope.interface import verify

from shoobx.immutable import pjpersist, immutable, interfaces


class IQuestion(zope.interface.Interface):

    question = zope.schema.TextLine(
        title='Question')

    answer = zope.schema.TextLine(
        title='Answer')


@zope.interface.implementer(IQuestion)
@serialize.table('questions')
class Question(pjpersist.Immutable):
    question = None #FieldProperty(IQuestion['question'])
    answer = None #FieldProperty(IQuestion['answer'])

    def __init__(self, question=None, answer=None):
        if question is not None:
            self.question = question
        if answer is not None:
            self.answer = answer


class Questions(pjpersist.ImmutableContainer):
    _pj_table = 'questions'


class NoOpPropertyTest(unittest.TestCase):

    def test_get(self):
        prop = pjpersist.NoOpProperty()
        # No-op.
        self.assertIsNone(prop.__get__(object(), object))

    def test_set(self):
        prop = pjpersist.NoOpProperty()
        # No-op.
        prop.__set__(object(), 42)

    def test_delete(self):
        prop = pjpersist.NoOpProperty()
        # No-op.
        prop.__delete__(object())


class ImmutableTest(unittest.TestCase):

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(
                interfaces.IImmutable,
                pjpersist.Immutable))
        self.assertTrue(
            verify.verifyClass(
                interfaces.IRevisionedImmutable,
                pjpersist.Immutable))

    def test_im_manager(self):
        im = pjpersist.Immutable()
        im.__parent__ = parent = object()
        self.assertIs(im.__im_manager__, parent)

    def test_im_is_internal_attr(self):
        im = pjpersist.Immutable()
        self.assertTrue(im.__im_is_internal_attr__('_p_oid'))
        self.assertTrue(im.__im_is_internal_attr__('_v_name'))
        self.assertTrue(im.__im_is_internal_attr__('__name__'))
        self.assertTrue(im.__im_is_internal_attr__('name'))
        self.assertFalse(im.__im_is_internal_attr__('answer'))

    def test_im_clone(self):
        im = pjpersist.Immutable(im_finalize=False)
        im.answer = 42
        im._p_oid = 1
        clone = im.__im_clone__()
        self.assertEqual(clone.answer, 42)
        self.assertIsNone(clone._p_oid)

    def test_pj_get_column_fields(self):
        im = pjpersist.Immutable(im_finalize=False)
        im.name = 'question'
        im.__im_start_on__ = datetime.datetime(2019, 5, 29, 2, 0)
        im.__im_end_on__ = datetime.datetime(2019, 5, 29, 3, 0)
        im.__im_creator__ = 'universe'
        im.__im_comment__ = 'Give answer.'
        self.assertDictEqual(
            im._pj_get_column_fields(),
            {
                'name': 'question',
                'version': 0,
                'startOn': datetime.datetime(2019, 5, 29, 2, 0),
                'endOn': datetime.datetime(2019, 5, 29, 3, 0),
                'creator': 'universe',
                'comment': 'Give answer.',
            }
        )

    def test_getstate(self):
        im = pjpersist.Immutable(im_finalize=False)
        im.name = 'question'
        im.answer = 42
        im.__im_start_on__ = datetime.datetime(2019, 5, 29, 2, 0)
        self.assertDictEqual(
            im.__getstate__(),
            {
                '__im_start_on__': datetime.datetime(2019, 5, 29, 2, 0),
                'name': 'question',
                'answer': 42,
            })

    def test_setstate(self):
        im = pjpersist.Immutable(im_finalize=False)
        im.__setstate__({'name': 'question', 'answer': 42, })
        self.assertEqual(im.name, 'question')
        self.assertEqual(im.answer, 42)

    def test_repr(self):
        im = pjpersist.Immutable(im_finalize=False)
        im.__name__ = 'question'
        im._p_oid = '012789abcdef'
        self.assertEqual(
            im.__repr__(), '<Immutable (question) at 012789abcdef>')


class ImmutableContainerTest(unittest.TestCase):

    def setUp(self):
        self.conn = mock.MagicMock(
            dsn='postgresql://localhost/db')
        self.dm = datamanager.PJDataManager(self.conn)
        self.cont = pjpersist.ImmutableContainer()
        self.cont._p_jar = self.dm
        self.cont._pj_table = 'table'

    def test_p_pj_table(self):
        self.assertEqual(self.cont._p_pj_table, 'table')

    def test_pj_get_resolve_filter(self):
        flt = self.cont._pj_get_resolve_filter()
        self.assertEqual(
            flt.__sqlrepr__('postgres'),
            "(((table.data) ? ('name')) AND ((table.endOn) IS NULL))"
        )

    def test_load_one(self):
        self.cont._cache['question'] = im = pjpersist.Immutable()
        im._p_jar = self.dm
        loaded = self.cont._load_one(
            'q1', {'name': 'question', 'answer': 42})
        self.assertIs(im, loaded)
        self.assertEqual(loaded.name, 'question')
        self.assertEqual(loaded.answer, 42)

    def test_add(self):
        im = pjpersist.Immutable()
        self.cont.add(im)
        self.assertIn(
            id(im), self.dm._registered_objects)
        self.assertIsNotNone(im.__im_start_on__)
        self.assertIsNone(im.__im_end_on__)

    def test_getCurrentRevision(self):
        im = pjpersist.Immutable()
        self.cont.add(im)
        self.assertIs(self.cont.getCurrentRevision(im), im)

class ImmutableDatabaseTest(testing.PJTestCase):

    def setUp(self):
        super().setUp()
        dm = self.dm

        # since the table gets created in PJContainer.__init__ we need to
        # provide a IPJDataManagerProvider
        @zope.interface.implementer(pjinterfaces.IPJDataManagerProvider)
        class Provider:

            def get(self, database):
                return dm

        zope.component.provideUtility(Provider())
        self.questions = Questions()

    def test_raw_find(self):
        q1 = Question('What is the answer')
        self.questions.add(q1)
        with q1.__im_update__(comment='Provide Answer') as q2:
            q2.answer = 42
        transaction.commit()
        result = list(self.questions.raw_find(
            fields=('id', 'name', 'data', 'comment')))
        self.assertEqual(result[0]['data']['answer'], 42)
        self.assertEqual(result[0]['data']['question'], 'What is the answer')
        self.assertEqual(result[0]['comment'], 'Provide Answer')
        self.assertEqual(
            list(result[0].keys()), ['id', 'name', 'data', 'comment'])

    def test_getCurrentRevision(self):
        q = Question('What is the answer')
        self.questions.add(q)
        transaction.commit()
        cur = self.questions.getCurrentRevision(q)
        self.assertEqual(q._p_oid, cur._p_oid)

    def test_getRevisionHistory(self):
        q = Question('What is the answer')
        self.questions.add(q)
        transaction.commit()
        history = list(self.questions.getRevisionHistory(q))
        self.assertEqual(len(history), 1)
        self.assertEqual(q._p_oid, history[0]._p_oid)

    def test_rollbackToRevision(self):
        q1 = Question('What is the answer')
        self.questions.add(q1)
        with q1.__im_update__() as q2:
            q2.answer = 42
        transaction.commit()
        self.assertEqual(
            self.questions.getCurrentRevision(q1)._p_oid, q2._p_oid)

        self.questions.rollbackToRevision(q1, activate=True)
        transaction.commit()
        cur = self.questions.getCurrentRevision(q1)
        self.assertEqual(cur._p_oid, q1._p_oid)
        self.assertEqual(cur.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertIsNone(cur.__im_end_on__)

    def test_rollbackToRevision_doNotActivate(self):
        q1 = Question('What is the answer')
        self.questions.add(q1)
        with q1.__im_update__() as q2:
            q2.answer = 42
        transaction.commit()
        self.questions.rollbackToRevision(q1, activate=False)
        transaction.commit()
        with self.assertRaises(KeyError):
            cur = self.questions.getCurrentRevision(q1)

    def test_addRevision(self):
        q1 = Question('What is the answer')
        self.questions.add(q1)
        q2 = q1.__im_clone__()
        self.questions.addRevision(q2, old=q1)
        self.assertEqual(q1.__im_state__, interfaces.IM_STATE_RETIRED)
        self.assertIsNotNone(q1.__im_end_on__)
        self.assertEqual(q2.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertIsNone(q2.__im_end_on__)

    def test_functional(self):
        q = Question('What is the answer')
        self.questions.add(q)
        self.assertTrue(len(self.questions), 1)

        with q.__im_update__() as q2:
            q2.answer = 42
            q2.cast = {'computer': 'one', 'receiver': 'adent'}

        self.assertEqual(q2.answer, 42)
        self.assertDictEqual(
            dict(q2.cast), {'computer': 'one', 'receiver': 'adent'})
        self.assertIsInstance(q2.cast, immutable.ImmutableDict)
        self.assertEqual(q2.cast.__im_mode__, interfaces.IM_MODE_SLAVE)

        self.assertTrue(len(self.questions), 1)
        self.assertEqual(q.__im_state__, interfaces.IM_STATE_RETIRED)
        self.assertEqual(q2.__im_state__, interfaces.IM_STATE_LOCKED)

        self.assertIs(self.questions[q.__name__], q2)

        transaction.commit()

        q3 = self.questions[q.__name__]
        self.assertEqual(q3.answer, 42)
        self.assertDictEqual(
            dict(q3.cast), {'computer': 'one', 'receiver': 'adent'})

        revs = list(self.questions.getRevisionHistory(q3))
        self.assertEqual(len(revs), 2)
        rev1, rev2 = revs
        self.assertNotEqual(rev1._p_oid.id, rev2._p_oid.id)
        self.assertEqual(rev1.__name__, rev2.__name__)
        self.assertIsNotNone(rev1.__im_end_on__)
        self.assertIsNone(rev2.__im_end_on__)

        self.questions.rollbackToRevision(rev1, activate=True)
        transaction.commit()

        revs = list(self.questions.getRevisionHistory(q3))
        self.assertEqual(len(revs), 1)
        rev1, = revs
        self.assertIsNone(rev1.__im_end_on__)
        self.assertEqual(rev1._p_oid.id, q._p_oid.id)
