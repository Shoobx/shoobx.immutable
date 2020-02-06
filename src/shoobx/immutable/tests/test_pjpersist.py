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
import pjpersist.sqlbuilder as sb
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

    category = zope.schema.TextLine(
        title='Category')


@zope.interface.implementer(IQuestion)
@serialize.table('questions')
class Question(pjpersist.Immutable):
    question = None  # FieldProperty(IQuestion['question'])
    answer = None  # FieldProperty(IQuestion['answer'])
    category = None  # FieldProperty(IQuestion['category'])

    def __init__(self, question=None, answer=None, category=None):
        if question is not None:
            self.question = question
        if answer is not None:
            self.answer = answer
        if category is not None:
            self.category = category


class Questions(pjpersist.ImmutableContainer):
    _pj_table = 'questions'


class TransientCategorizedQuestions(pjpersist.ImmutableContainer):
    _pj_table = 'questions'
    category = None

    def __init__(self, category):
        self.category = category

    def _byCategoryQuery(self):
        datafld = sb.Field(self._pj_table, 'data')
        qry = sb.JGET(datafld, 'category') == self.category
        return qry

    def _pj_get_resolve_filter(self):
        qry = self._byCategoryQuery()
        immutable_filter = super()._pj_get_resolve_filter()
        return self._combine_filters(qry, immutable_filter)

    def _pj_get_resolve_filter_all_versions(self):
        qry = self._byCategoryQuery()
        immutable_filter = super()._pj_get_resolve_filter_all_versions()
        return self._combine_filters(qry, immutable_filter)


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

    def test_verifyInterface(self):
        self.assertTrue(
            verify.verifyClass(
                interfaces.IRevisionedImmutableManager,
                pjpersist.ImmutableContainer))

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

    def test_getRevision(self):
        q = Question('What is the answer')
        self.questions.add(q)
        with q.__im_update__() as q2:
            pass
        self.assertEqual(
            self.questions.getRevision(q.__name__, 0), q)
        self.assertEqual(
            self.questions.getRevision(q.__name__, 1), q2)

    def test_getNumberOfRevisions(self):
        q = Question('What is the answer')
        self.questions.add(q)
        transaction.commit()
        self.assertEqual(self.questions.getNumberOfRevisions(q), 1)

    def test_getRevisionHistory(self):
        q = Question('What is the answer')
        self.questions.add(q)
        transaction.commit()
        history = list(self.questions.getRevisionHistory(q))
        self.assertEqual(len(history), 1)
        self.assertEqual(q._p_oid, history[0]._p_oid)

    def test_getRevisionHistory_withCreator(self):
        q = Question('What is the answer')
        self.questions.add(q)
        with q.__im_update__(creator='someone') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, creator='someone')),
            [q2])

    def test_getRevisionHistory_withComment(self):
        q = Question('What is the answer')
        self.questions.add(q)
        with q.__im_update__(comment='Some important update') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, comment='important')),
            [q2])

    def test_getRevisionHistory_withStartBefore(self):
        q = Question('What is the answer')
        self.questions.now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        self.questions.now = now = lambda: datetime.datetime(2020, 1, 2)
        with q.__im_update__(comment='Some important update') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, startBefore=now())),
            [q])

    def test_getRevisionHistory_withStartAfter(self):
        q = Question('What is the answer')
        self.questions.now = now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        self.questions.now = lambda: datetime.datetime(2020, 1, 2)
        with q.__im_update__(comment='Some important update') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, startAfter=now())),
            [q2])

    def test_getRevisionHistory_withReversed(self):
        q = Question('What is the answer')
        self.questions.now = now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        with q.__im_update__(creator='someone') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, reversed=True)),
            [q2, q])

    def test_getRevisionHistory_withBatching(self):
        q = Question('What is the answer')
        self.questions.now = now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        with q.__im_update__() as q2:
            pass
        with q2.__im_update__() as q3:
            pass
        with q3.__im_update__() as q4:
            pass
        with q4.__im_update__() as q5:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, batchSize=2)),
            [q, q2])
        self.assertListEqual(
            list(self.questions.getRevisionHistory(
                    q, batchStart=2, batchSize=2)),
            [q3, q4])

    def test_rollbackToRevision(self):
        q1 = Question('What is the answer')
        self.questions.add(q1)
        with q1.__im_update__() as q2:
            q2.answer = 42
        transaction.commit()
        self.assertEqual(
            self.questions.getCurrentRevision(q1)._p_oid, q2._p_oid)

        anotherq = Question('Another trivia')
        self.questions.add(anotherq)

        with anotherq.__im_update__() as anotherq2:
            anotherq2.answer = 9
        transaction.commit()

        with anotherq2.__im_update__() as anotherq3:
            anotherq3.answer = 3
        transaction.commit()

        self.questions.rollbackToRevision(q1, activate=True)
        transaction.commit()
        cur = self.questions.getCurrentRevision(q1)
        self.assertEqual(cur._p_oid, q1._p_oid)
        self.assertEqual(cur.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertIsNone(cur.__im_end_on__)

        anotherCur = self.questions.getCurrentRevision(anotherq)
        self.assertEqual(anotherCur._p_oid, anotherq3._p_oid)

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
        self.assertEqual(len(self.questions), 1)

        with q.__im_update__() as q2:
            q2.answer = 42
            q2.cast = {'computer': 'one', 'receiver': 'adent'}

        self.assertEqual(q2.answer, 42)
        self.assertDictEqual(
            dict(q2.cast), {'computer': 'one', 'receiver': 'adent'})
        self.assertIsInstance(q2.cast, immutable.ImmutableDict)
        self.assertEqual(q2.cast.__im_mode__, interfaces.IM_MODE_SLAVE)

        self.assertEqual(len(self.questions), 1)
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

    def test_delete(self):
        q1 = Question('What is the answer')
        self.questions.add(q1)
        self.assertEqual(len(self.questions), 1)
        with q1.__im_update__() as q2:
            q2.answer = 42
        transaction.commit()
        self.assertEqual(len(self.questions), 1)
        self.assertEqual(q1.__name__, q2.__name__)

        anotherq = Question('Another trivia')
        self.questions.add(anotherq)

        with anotherq.__im_update__() as anotherq2:
            anotherq2.answer = 9
        transaction.commit()

        with anotherq2.__im_update__() as anotherq3:
            anotherq3.answer = 3
        transaction.commit()

        self.assertEqual(len(self.questions), 2)

        cur = self.questions._pj_jar.getCursor()

        # read directly the table to avoid any filtering by pjpersist
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 2+3)  # 2 revs of q1, 3 of anotherq

        # delete the object
        del self.questions[q1.__name__]
        self.assertEqual(len(self.questions), 1)

        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())

        # that should delete all revisions
        self.assertEqual(len(result), 3)  # 3 revs of anotherq

    def test_delete_categorized(self):
        # revision delete must take _pj_get_resolve_filter into account
        # just in case we have the same `name` in more Transient containers
        qnsMath = TransientCategorizedQuestions('math')

        qMath1 = Question('1+1', '2', 'math')
        qMath1.name = 'basic'
        qnsMath.add(qMath1)
        transaction.commit()
        with qMath1.__im_update__() as qMath1:
            qMath1.answer = 2
        transaction.commit()

        qMath2 = Question('5*4', '20', 'math')
        qMath2.name = 'second'
        qnsMath.add(qMath2)
        transaction.commit()
        with qMath2.__im_update__() as qMath2:
            qMath2.answer = 20
        transaction.commit()

        qnsLang = TransientCategorizedQuestions('language')
        qLang1 = Question('table', 'der tisch', 'language')
        qLang1.name = 'basic'
        qnsLang.add(qLang1)
        transaction.commit()
        with qLang1.__im_update__() as qLang1:
            qLang1.answer = 'der Tisch'
        transaction.commit()

        qLang2 = Question('window', 'das Fenster', 'language')
        qLang2.name = 'second'
        qnsLang.add(qLang2)
        transaction.commit()

        qLang3 = Question('world', 'die Welt', 'language')
        qnsLang.add(qLang3)
        transaction.commit()

        qHist1 = Question('Rome founded', '21 April 753', 'history')
        with qHist1.__im_update__() as qHist1:
            qHist1.answer = '21 April 753 BCE'
        qnsHist = TransientCategorizedQuestions('history')
        qnsHist.add(qHist1)
        transaction.commit()

        self.assertEqual(len(qnsMath), 2)
        self.assertEqual(len(qnsLang), 3)
        self.assertEqual(len(qnsHist), 1)

        # count all versions
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 4+4+1)

        # remove just the ONE Question from math
        del qnsMath['basic']
        transaction.commit()

        # reload all containers so caches don't spoil the picture
        qnsMath = TransientCategorizedQuestions('math')
        qnsLang = TransientCategorizedQuestions('language')
        qnsHist = TransientCategorizedQuestions('history')

        self.assertEqual(len(qnsMath), 1)
        self.assertEqual(len(qnsLang), 3)
        self.assertEqual(len(qnsHist), 1)

        # count all versions
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 2+4+1)

        # clear just the language Questions
        qnsLang.clear()
        transaction.commit()

        # reload all containers so caches don't spoil the picture
        qnsMath = TransientCategorizedQuestions('math')
        qnsLang = TransientCategorizedQuestions('language')
        qnsHist = TransientCategorizedQuestions('history')

        self.assertEqual(len(qnsMath), 1)
        self.assertEqual(len(qnsLang), 0)
        self.assertEqual(len(qnsHist), 1)

        # count all versions
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 2+0+1)
