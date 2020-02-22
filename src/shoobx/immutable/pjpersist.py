###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""pjpersist Container of Immutables.
"""
import datetime
import zope.interface
import zope.schema
import pjpersist.sqlbuilder as sb
from pjpersist import interfaces as pjinterfaces
from pjpersist.zope import container as pjcontainer

from shoobx.immutable import interfaces, revisioned


class NoOpProperty:

    def __get__(self, inst, cls):
        return None

    def __set__(self, inst, value):
        pass

    def __delete__(self, inst):
        pass


class Version(zope.schema.Int):
    # Unfortuantely, default Int._type is a tuple.
    _type = int


@zope.interface.implementer(pjinterfaces.IColumnSerialization)
class Immutable(revisioned.RevisionedImmutable, pjcontainer.PJContained):

    # Behave like a persistent object, but without the change notifications.
    _p_oid = None
    _p_jar = None
    _p_changed = NoOpProperty()
    _pj_name = 'name'

    # The below fields are used to auto create the SQL table names.They must
    # be in sync with `ImmutableContainer._pj_column_fields`. `id` and `data`
    # can be omitted.
    _pj_column_fields = (
        zope.schema.TextLine(__name__=_pj_name),
        Version(__name__='version'),
        zope.schema.Datetime(__name__='startOn'),
        zope.schema.Datetime(__name__='endOn'),
        zope.schema.TextLine(__name__='creator'),
        zope.schema.Text(__name__='comment'),
    )

    @property
    def __im_manager__(self):
        return self.__parent__

    def __im_is_internal_attr__(self, name):
        if name.startswith('_v_') or name.startswith('_p_'):
            return True
        if name == self._pj_name:
            return True
        return super().__im_is_internal_attr__(name)

    def __im_clone__(self):
        clone = super().__im_clone__()
        clone._p_oid = None
        return clone

    def _pj_get_column_fields(self):
        return {
            self._pj_name: getattr(self, self._pj_name),
            'version': self.__im_version__,
            'startOn': self.__im_start_on__,
            'endOn': self.__im_end_on__,
            'creator': self.__im_creator__,
            'comment': self.__im_comment__,
        }

    def __getstate__(self):
        return {
            name: value
            for name, value in self.__dict__.items()
            if (not name.startswith('_v_')
                and not name.startswith('_p_')
                and not name.startswith('_pj_'))
        }

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __repr__(self):
        return f'<{self.__class__.__name__} ({self.__name__}) at {self._p_oid}>'


@zope.interface.implementer(interfaces.IRevisionedImmutableManager)
class ImmutableContainer(pjcontainer.AllItemsPJContainer):

    _pj_mapping_key = Immutable._pj_name

    # These fields are used to determine whether to take native SQL columns
    # instead of JSONB fields in raw_find.
    _pj_column_fields = pjcontainer.AllItemsPJContainer._pj_column_fields + (
        tuple([fld.__name__ for fld in Immutable._pj_column_fields]))

    # Testing hook.
    now = datetime.datetime.now

    @property
    def _p_pj_table(self):
        return self._pj_table

    def _pj_get_resolve_filter_all_versions(self):
        # Return a query that matches all versions, not just the current one
        # as opposed to `_pj_get_resolve_filter`.
        return super()._pj_get_resolve_filter()

    def _pj_get_resolve_filter(self):
        # Return a filter that matches ONLY the current version.
        qry = self._pj_get_resolve_filter_all_versions()
        endOnFld = sb.Field(self._pj_table, 'endOn')
        return self._combine_filters(qry, endOnFld == None)  # noqa E711

    def _load_one(self, id, doc, use_cache=True):
        obj = super()._load_one(id, doc, use_cache=use_cache)
        obj._p_jar.setstate(obj, doc)
        return obj

    def add(self, obj, key=None):
        assert obj.__im_state__ == interfaces.IM_STATE_LOCKED, obj.__im_state__

        res = super().add(obj, key)
        self.addRevision(obj)
        return res

    def getCurrentRevision(self, obj):
        return self[obj.__name__]

    def getRevision(self, name, version):
        qry = self._combine_filters(
            self._pj_get_resolve_filter_all_versions(),
            sb.Field(self._pj_table, self._pj_mapping_key) == name,
            sb.Field(self._pj_table, 'version') == version,
        )
        with self._pj_jar.getCursor() as cur:
            cur.execute(
                sb.Select(self._get_sb_fields(()), qry),
                flush_hint=[self._pj_table])
            row = cur.fetchone()
        return self._load_one(
            row[self._pj_id_column], row[self._pj_data_column], use_cache=False)

    def getNumberOfRevisions(self, obj):
        # 1. Setup the basic query.
        qry = self._combine_filters(
            self._pj_get_resolve_filter_all_versions(),
            sb.Field(self._pj_table, self._pj_mapping_key) == obj.__name__
        )
        with self._pj_jar.getCursor() as cur:
            cur.execute(sb.Select('COUNT(*)', qry), flush_hint=[self._pj_table])
            return cur.fetchone()[0]

    def getRevisionHistory(
            self, obj, creator=None, comment=None,
            startBefore=None, startAfter=None,
            batchStart=0, batchSize=None, reversed=False):

        # 1. Setup the basic query.
        qry = self._combine_filters(
            self._pj_get_resolve_filter_all_versions(),
            sb.Field(self._pj_table, self._pj_mapping_key) == obj.__name__
        )

        # 2. Apply all additional filters.
        if creator is not None:
            creatorFld = sb.Field(self._pj_table, 'creator')
            qry = self._combine_filters(qry, creatorFld == creator)
        if comment is not None:
            commentFld = sb.Field(self._pj_table, 'comment')
            qry = self._combine_filters(qry, commentFld.contains(comment))
        if startBefore is not None:
            startOnFld = sb.Field(self._pj_table, 'startOn')
            qry = self._combine_filters(qry, startOnFld < startBefore)
        if startAfter is not None:
            startOnFld = sb.Field(self._pj_table, 'startOn')
            qry = self._combine_filters(qry, startOnFld > startAfter)

        # 3. Setup ordering.
        orderBy = sb.Field(self._pj_table, 'version')
        fields = self._get_sb_fields(())

        # 4. Apply batching.
        batchEnd = None
        if batchSize is not None:
            batchEnd = batchStart + batchSize

        # 5. Execute query.
        with self._pj_jar.getCursor() as cur:
            cur.execute(
                sb.Select(
                    fields, qry, start=batchStart, end=batchEnd,
                    orderBy=orderBy, reversed=reversed),
                flush_hint=[self._pj_table])
            for row in cur:
                obj = self._load_one(
                    row[self._pj_id_column], row[self._pj_data_column],
                    use_cache=False)
                yield obj

    def rollbackToRevision(self, revision, activate=False):
        cur = self._pj_jar.getCursor()
        qry = self._combine_filters(
            self._pj_get_resolve_filter_all_versions(),
            sb.Field(self._pj_table, "version") > revision.__im_version__,
            sb.Field(self._pj_table, self._pj_mapping_key) == revision.__name__
        )
        # this DELETE works fine just because `execute` checks all SQL commands
        # and calls PJDataManager.setDirty accordingly
        # OTOH not sure that deleting directly is 100% because
        # pjpersist `PJDataManager.remove` does a bit more than just a
        # SQL DELETE
        cur.execute(sb.Delete(self._pj_table, qry))
        revision.__im_state__ = interfaces.IM_STATE_LOCKED
        if activate:
            revision.__im_end_on__ = None
        self._pj_jar.register(revision)
        self._cache[revision.__name__] = revision

    def addRevision(self, new, old=None):
        assert new.__im_state__ == interfaces.IM_STATE_LOCKED, new.__im_state__

        now = self.now()
        if old is not None:
            old.__im_end_on__ = now
            old.__im_state__ = interfaces.IM_STATE_RETIRED
            self._pj_jar.register(old)

        new.__im_start_on__ = now
        self._pj_jar.register(new)
        self._cache[new.__name__] = new

    def __setitem__(self, key, value):
        assert value.__im_state__ == interfaces.IM_STATE_LOCKED, \
               value.__im_state__
        super().__setitem__(key, value)

    def __delitem__(self, key):
        super().__delitem__(key)

        # We need to make sure that all revisions get deleted.
        cur = self._pj_jar.getCursor()
        qry = self._combine_filters(
            self._pj_get_resolve_filter_all_versions(),
            sb.Field(self._pj_table, self._pj_mapping_key) == key
        )
        # This DELETE works fine just because `execute()` checks all SQL
        # commands and calls `PJDataManager.setDirty()` accordingly.
        cur.execute(sb.Delete(self._pj_table, qry))
