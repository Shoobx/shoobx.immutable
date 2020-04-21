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


class NoRemovalQuestions(pjpersist.ImmutableContainer):
    _pj_table = 'questions'
    _pj_remove_documents = False


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
                interfaces.IRevisionedImmutable,
                pjpersist.Immutable))

    def test_im_manager(self):
        with pjpersist.Immutable.__im_create__() as factory:
            im = factory()
        im.__parent__ = parent = object()
        self.assertIs(im.__im_manager__, parent)

    def test_im_is_internal_attr(self):
        with pjpersist.Immutable.__im_create__() as factory:
            im = factory()
        self.assertTrue(im.__im_is_internal_attr__('_p_oid'))
        self.assertTrue(im.__im_is_internal_attr__('_v_name'))
        self.assertTrue(im.__im_is_internal_attr__('__name__'))
        self.assertTrue(im.__im_is_internal_attr__('name'))
        self.assertFalse(im.__im_is_internal_attr__('answer'))

    def test_im_clone(self):
        with pjpersist.Immutable.__im_create__(finalize=False) as factory:
            im = factory()
        im.answer = 42
        im._p_oid = 1
        clone = im.__im_clone__()
        self.assertEqual(clone.answer, 42)
        self.assertIsNone(clone._p_oid)

    def test_pj_get_column_fields(self):
        with pjpersist.Immutable.__im_create__(finalize=False) as factory:
            im = factory()
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
                'state': 'transient',
                'creator': 'universe',
                'comment': 'Give answer.',
            }
        )

    def test_getstate(self):
        with pjpersist.Immutable.__im_create__(finalize=False) as factory:
            im = factory()
        im.name = 'question'
        im.answer = 42
        im.__im_start_on__ = datetime.datetime(2019, 5, 29, 2, 0)
        self.assertDictEqual(
            im.__getstate__(),
            {
                '__im_comment__': None,
                '__im_creator__': None,
                '__im_start_on__': datetime.datetime(2019, 5, 29, 2, 0),
                'name': 'question',
                'answer': 42,
            })

    def test_setstate(self):
        with pjpersist.Immutable.__im_create__(finalize=False) as factory:
            im = factory()
        im.__setstate__({'name': 'question', 'answer': 42, })
        self.assertEqual(im.name, 'question')
        self.assertEqual(im.answer, 42)

    def test_repr(self):
        with pjpersist.Immutable.__im_create__(finalize=False) as factory:
            im = factory()
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

    def test_pj_column_fields(self):
        self.assertEqual(
            pjpersist.ImmutableContainer._pj_column_fields,
            ('id', 'data',
             'name', 'version', 'state', 'startOn', 'endOn',
             'creator', 'comment'))

        self.assertEqual(
            pjpersist.ImmutableContainer._pj_mapping_key,
            'name')

    def test_p_pj_table(self):
        self.assertEqual(self.cont._p_pj_table, 'table')

    def test_pj_get_resolve_filter(self):
        flt = self.cont._pj_get_resolve_filter()
        self.assertEqual(
            flt.__sqlrepr__('postgres'),
            "((table.endOn) IS NULL)"
        )

    def test_pj_get_resolve_filter_withDeletedItems(self):
        self.cont._pj_with_deleted_items = True
        flt = self.cont._pj_get_resolve_filter()
        self.assertEqual(
            flt.__sqlrepr__('postgres'),
            "(((table.endOn) IS NULL) OR ((table.state) = ('deleted')))"
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
        with pjpersist.Immutable.__im_create__() as factory:
            im = factory()

        self.cont.add(im)

        self.assertIn(
            id(im), self.dm._registered_objects)
        self.assertIsNotNone(im.__im_start_on__)
        self.assertIsNone(im.__im_end_on__)

    def test_add_withTransientObject(self):
        im = pjpersist.Immutable()
        self.assertNotEqual(im.__im_state__, interfaces.IM_STATE_LOCKED)
        # Objects in a non-locked state *cannot* be added.
        with self.assertRaises(AssertionError):
            self.cont.add(im)

    def test_getCurrentRevision(self):
        with pjpersist.Immutable.__im_create__() as factory:
            im = factory()
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
        with Question.__im_create__() as factory:
            q1 = factory('What is the answer')
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
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.add(q)
        transaction.commit()
        cur = self.questions.getCurrentRevision(q)
        self.assertEqual(q._p_oid, cur._p_oid)

    def test_getRevision(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.add(q)
        with q.__im_update__() as q2:
            pass
        self.assertEqual(
            self.questions.getRevision(q.__name__, 0), q)
        self.assertEqual(
            self.questions.getRevision(q.__name__, 1), q2)

    def test_getNumberOfRevisions(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.add(q)
        transaction.commit()
        self.assertEqual(self.questions.getNumberOfRevisions(q), 1)

    def test_getRevisionHistory(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.add(q)
        transaction.commit()
        history = list(self.questions.getRevisionHistory(q))
        self.assertEqual(len(history), 1)
        self.assertEqual(q._p_oid, history[0]._p_oid)

    def test_getRevisionHistory_withCreator(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.add(q)
        with q.__im_update__(creator='someone') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, creator='someone')),
            [q2])

    def test_getRevisionHistory_withComment(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.add(q)
        with q.__im_update__(comment='Some important update') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, comment='important')),
            [q2])

    def test_getRevisionHistory_withStartBefore(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        self.questions.now = now = lambda: datetime.datetime(2020, 1, 2)
        with q.__im_update__(comment='Some important update'):
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, startBefore=now())),
            [q])

    def test_getRevisionHistory_withStartAfter(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.now = now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        self.questions.now = lambda: datetime.datetime(2020, 1, 2)
        with q.__im_update__(comment='Some important update') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, startAfter=now())),
            [q2])

    def test_getRevisionHistory_withReversed(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        with q.__im_update__(creator='someone') as q2:
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, reversed=True)),
            [q2, q])

    def test_getRevisionHistory_withBatching(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        self.questions.now = lambda: datetime.datetime(2020, 1, 1)
        self.questions.add(q)
        with q.__im_update__() as q2:
            pass
        with q2.__im_update__() as q3:
            pass
        with q3.__im_update__() as q4:
            pass
        with q4.__im_update__():
            pass
        self.assertListEqual(
            list(self.questions.getRevisionHistory(q, batchSize=2)),
            [q, q2])
        self.assertListEqual(
            list(self.questions.getRevisionHistory(
                    q, batchStart=2, batchSize=2)),
            [q3, q4])

    def test_rollbackToRevision(self):
        with Question.__im_create__() as factory:
            q1 = factory('What is the answer')
        self.questions.add(q1)
        with q1.__im_update__() as q2:
            q2.answer = 42
        transaction.commit()
        self.assertEqual(
            self.questions.getCurrentRevision(q1)._p_oid, q2._p_oid)

        with Question.__im_create__() as factory:
            anotherq = factory('Another trivia')
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
        with Question.__im_create__() as factory:
            q1 = factory('What is the answer')
        self.questions.add(q1)
        with q1.__im_update__() as q2:
            q2.answer = 42
        transaction.commit()
        self.questions.rollbackToRevision(q1, activate=False)
        transaction.commit()
        with self.assertRaises(KeyError):
            self.questions.getCurrentRevision(q1)

    def test_addRevision(self):
        with Question.__im_create__() as factory:
            q1 = factory('What is the answer')
        self.questions.add(q1)

        with q1.__im_update__() as q2:
            q2.answer = 42

        self.questions.addRevision(q2, old=q1)

        self.assertEqual(q1.__im_state__, interfaces.IM_STATE_RETIRED)
        self.assertIsNotNone(q1.__im_end_on__)
        self.assertEqual(q2.__im_state__, interfaces.IM_STATE_LOCKED)
        self.assertIsNone(q2.__im_end_on__)

    def test_addRevision_withTransientObject(self):
        with Question.__im_create__() as factory:
            q1 = factory('What is the answer')
        self.questions.add(q1)

        q2 = q1.__im_clone__()
        self.assertNotEqual(q2.__im_state__, interfaces.IM_STATE_LOCKED)

        # Objects in a non-locked state *cannot* be added.
        with self.assertRaises(AssertionError):
            self.questions.addRevision(q2, old=q1)

        self.assertEqual(q2.__im_state__, interfaces.IM_STATE_TRANSIENT)
        self.assertIsNone(q2.__im_end_on__)

    def test_withDeletedItems(self):
        questions = self.questions.withDeletedItems()
        # We create a clone. That's by design to not modify the priginal
        # container and to reset the cache properly.
        self.assertIsNot(questions, self.questions)
        self.assertEqual(questions._pj_with_deleted_items, True)

    def test_setitem(self):
        self.dm._ensure_sql_columns(Question(), 'questions')
        with Question.__im_create__() as factory:
            q1 = factory('What is the answer')

        self.questions['q1'] = q1
        self.assertEqual(list(self.questions), ['q1'])

    def test_setitem_withTransientObject(self):
        q1 = Question('What is the answer')
        self.assertNotEqual(q1.__im_state__, interfaces.IM_STATE_LOCKED)

        # Objects in a non-locked state *cannot* be added.
        with self.assertRaises(AssertionError):
            self.questions['q1'] = q1

    def test_delitem(self):
        # Create a question with multiple versions.
        with Question.__im_create__() as factory:
            q1_1 = factory('What is the answer')
        self.questions.add(q1_1)
        with q1_1.__im_update__() as q1_2:
            q1_2.answer = 42
        transaction.commit()
        self.assertEqual(len(self.questions), 1)
        self.assertEqual(q1_1.__name__, q1_2.__name__)

        # Create a second question with multiple versions.
        with Question.__im_create__() as factory:
            q2_1 = factory('What is 3 * 4?')
        self.questions.add(q2_1)
        with q2_1.__im_update__() as q2_2:
            q2_2.answer = 9
        with q2_2.__im_update__() as q2_3:
            q2_3.answer = 3
        transaction.commit()
        self.assertEqual(len(self.questions), 2)

        # Now let's look into the DB table directly to ensure that we have 5
        # rows, 2 versions of q1 and 3 versions of q2.
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 5)

        # Let's now delete q1.
        del self.questions[q1_2.__name__]
        self.assertEqual(len(self.questions), 1)

        # Let's check the DB table again. All revisions of q1 should be
        # deleted, which means we should only see 3 rows for the 3 revisions
        # of q2.
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 3)

    def test_delitem_withAdditionalQueryFilter(self):
        self.dm._ensure_sql_columns(Question(), 'questions')

        # Create a new topic container with two questions.
        qns1 = TransientCategorizedQuestions('topic1')

        with Question.__im_create__() as factory:
            q1_1 = factory("What is the answer?", '42', 'topic1')
            q1_2 = factory("What iss the real answer?", 'unknown', 'topic1')
        qns1.add(q1_1, key='q1')
        qns1.add(q1_2, key='q2')
        transaction.commit()
        self.assertEqual(len(qns1), 2)

        # Create a second topic with three more  questions. Note that the
        # first two questions have the same name as the questions in topic 1.
        qns2 = TransientCategorizedQuestions('topic2')
        with Question.__im_create__() as factory:
            q2_1 = factory("Is Earth gone?", 'yes', 'topic2')
            q2_2 = factory("Is Mars gone?", 'no', 'topic2')
            q2_3 = factory("Is Pluto gone?", 'unknown', 'topic2')
        qns2.add(q2_1, key='q1')
        qns2.add(q2_2, key='q2')
        qns2.add(q2_3, key='q3')
        transaction.commit()
        self.assertEqual(len(qns2), 3)

        # Now let's look into the DB table directly to ensure that we have 5
        # rows, 2 objects from topic1 (1 version each) and 3 objects from
        # topic 2 (1 version each).
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 5)

        # Deletion -- whihc deletes all revisions of an object by name -- must
        # take `_pj_get_resolve_filter` into account, so that it does not
        # delete objects from another container.
        del qns1['q1']
        transaction.commit()

        # Reload all containers so caches don't spoil the picture.
        qns1 = TransientCategorizedQuestions('topic1')
        self.assertEqual(len(qns1), 1)
        qns2 = TransientCategorizedQuestions('topic2')
        self.assertEqual(len(qns2), 3)

        # Let's check the DB table again. All revisions of q1 in topic1 should
        # be deleted, which means we should only see 4 rows now, 1 row for q2
        # in topic 1 and 3 rows for the 3 questions in topic 2.
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 4)

        # Clearing a container should also not overstep its bounds.
        qns2.clear()
        transaction.commit()

        # Reload all containers so caches don't spoil the picture.
        qns1 = TransientCategorizedQuestions('topic1')
        self.assertEqual(len(qns1), 1)
        qns2 = TransientCategorizedQuestions('topic2')
        self.assertEqual(len(qns2), 0)

        # Let's check the DB table. This time only 1 row for q2 of topic 1
        # should be left.
        cur = self.questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 1)

    def test_delitem_withoutPjDocumentDeletion(self):
        questions = NoRemovalQuestions()
        # 2. Create a question with multiple versions.
        with Question.__im_create__() as factory:
            q1_1 = factory('What is the answer')
        questions.add(q1_1)
        with q1_1.__im_update__() as q1_2:
            q1_2.answer = 42
        transaction.commit()
        self.assertEqual(len(questions), 1)
        self.assertEqual(q1_1.__name__, q1_2.__name__)

        # Now let's look into the DB table directly to ensure that we have 2
        # rows, 2 versions of q1.
        cur = questions._pj_jar.getCursor()
        cur.execute("SELECT * FROM questions")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 2)

        # Let's now delete q1.
        del questions[q1_2.__name__]
        self.assertEqual(len(questions), 0)

        # Let's check the DB table again. We should still have 2 rows, but all
        # of them should have an end date and be in th eretired state.
        cur.execute("SELECT * FROM questions ORDER BY endon")
        result = list(cur.fetchall())
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0]['data']['__im_state__'], interfaces.IM_STATE_RETIRED)
        self.assertIsNotNone(
            result[1]['endon'])
        self.assertEqual(
            result[1]['data']['__im_state__'], interfaces.IM_STATE_DELETED)

    def test_functional(self):
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
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

    def test_functional_deletionAndRevival(self):
        # This test demonstrates how an object can be deleted and be revived
        # in no-document-removal mode of the container.
        questions = NoRemovalQuestions()
        with Question.__im_create__() as factory:
            q = factory('What is the answer')
        questions.add(q)
        qname = q.__name__
        self.assertEqual(len(questions), 1)
        del questions[qname]
        self.assertEqual(len(questions), 0)
        self.assertNotIn(qname, questions)

        # Now we switch the container to return deleted items as well.
        historical = questions.withDeletedItems()
        self.assertEqual(len(historical), 1)
        self.assertIn(qname, historical)
        dq = historical[qname]
        self.assertEqual(dq.__im_state__, interfaces.IM_STATE_DELETED)
        # We can even revert the deletion, which effectively revives it.
        historical.rollbackToRevision(dq, activate=True)
        dq = historical[qname]
        self.assertEqual(dq.__im_state__, interfaces.IM_STATE_LOCKED)
        # And it is available in the regualr container as well.
        self.assertEqual(len(questions), 1)
        self.assertIn(qname, questions)
